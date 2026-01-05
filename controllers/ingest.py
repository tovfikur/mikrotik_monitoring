# -*- coding: utf-8 -*-

import json
import logging
import hmac
import hashlib
from datetime import datetime

from odoo import http, fields, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class MikrotikIngestController(http.Controller):
    """High-throughput ingestion endpoint for collector service.
    
    Designed for ISP-grade performance:
    - Bulk metric ingestion
    - HMAC authentication
    - Minimal ORM overhead
    - Idempotent operations
    """

    @http.route(
        "/mikrotik/ingest/metrics",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def ingest_metrics(self, collector_id=None, signature=None, timestamp=None, devices=None, **kwargs):
        """Ingest telemetry metrics from collector.
        
        Expected payload:
        {
            "collector_id": "collector-01",
            "signature": "hmac-sha256-hex",
            "timestamp": "2026-01-05T10:00:01Z",
            "devices": [
                {
                    "device_uid": "MT-0001",
                    "ts": "2026-01-05T10:00:01Z",
                    "metrics": {
                        "system.cpu.load_pct": 23.5,
                        "iface.ether1.rx_bps": 4312332,
                        ...
                    }
                }
            ]
        }
        """
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            # Validate authentication
            if not self._validate_signature(data):
                return {"success": False, "error": "Authentication failed"}
            
            devices_data = devices or []
            if not devices_data:
                return {"success": False, "error": "No devices in payload"}
            
            # Process in sudo context for performance
            env = request.env(user=SUPERUSER_ID)
            
            total_metrics = 0
            errors = []
            
            for device_data in devices_data:
                try:
                    count = self._process_device_metrics(env, device_data)
                    total_metrics += count
                except Exception as e:
                    errors.append({
                        "device_uid": device_data.get("device_uid"),
                        "error": str(e),
                    })
                    _logger.warning("Error processing device %s: %s", 
                                    device_data.get("device_uid"), str(e))
            
            return {
                "success": True,
                "metrics_processed": total_metrics,
                "errors": errors if errors else None,
            }
            
        except Exception as e:
            _logger.exception("Ingest error")
            return {"success": False, "error": str(e)}

    def _validate_signature(self, data):
        """Validate HMAC signature from collector.
        
        For production, the secret should come from system parameters.
        """
        # Get secret from system parameters
        IrParam = request.env["ir.config_parameter"].sudo()
        secret = IrParam.get_param("mikrotik_monitoring.collector_secret", "")
        
        if not secret:
            # No secret configured - allow for development
            _logger.warning("No collector secret configured - allowing unauthenticated access")
            return True
        
        signature = data.get("signature", "")
        if not signature:
            return False
        
        # Create signature from payload
        collector_id = data.get("collector_id", "")
        timestamp = data.get("timestamp", "")
        message = f"{collector_id}:{timestamp}"
        
        expected = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)

    def _process_device_metrics(self, env, device_data):
        """Process metrics for a single device."""
        device_uid = device_data.get("device_uid")
        ts_str = device_data.get("ts")
        metrics = device_data.get("metrics", {})
        
        if not device_uid or not metrics:
            return 0
        
        # Find device
        Device = env["mikrotik.device"]
        device = Device.search([("device_uid", "=", device_uid)], limit=1)
        
        if not device:
            _logger.debug("Unknown device UID: %s", device_uid)
            return 0
        
        # Parse timestamp - Odoo expects naive datetime (assumes UTC)
        ts_collected = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # Convert to naive datetime by removing tzinfo
        if ts_collected.tzinfo is not None:
            ts_collected = ts_collected.replace(tzinfo=None)
        
        # Update device last_seen
        device.write({
            "last_seen": ts_collected,
            "state": "up",
        })
        
        # Get metric catalog for IDs
        MetricCatalog = env["mikrotik.metric.catalog"]
        MetricLatest = env["mikrotik.metric.latest"]
        MetricPoint = env["mikrotik.metric.point"]
        
        # Prepare points for bulk insert
        points = []
        latest_updates = {}
        
        for metric_key, value in metrics.items():
            # Parse interface from key if present (e.g., "iface.ether1.rx_bps")
            interface_name = None
            base_key = metric_key
            
            if metric_key.startswith("iface.") and metric_key.count(".") >= 2:
                parts = metric_key.split(".", 2)
                interface_name = parts[1]
                base_key = f"iface.{parts[2]}"
            
            # Get or create metric ID
            metric_id = MetricCatalog.get_metric_id(base_key)
            
            # Prepare for time-series storage
            points.append({
                "device_id": device.id,
                "metric_id": metric_id,
                "interface_name": interface_name,
                "ts_collected": ts_collected,
                "value_float": float(value) if isinstance(value, (int, float)) else None,
                "value_text": str(value) if not isinstance(value, (int, float)) else None,
            })
            
            # Prepare for latest table
            latest_key = f"{base_key}:{interface_name or ''}"
            latest_updates[latest_key] = {
                "metric_key": base_key,
                "interface_name": interface_name,
                "value": value,
            }
        
        # Bulk insert to time-series table
        if points:
            MetricPoint.bulk_create(points)
        
        # Update latest table
        for key, data in latest_updates.items():
            MetricLatest._upsert_single(
                device.id,
                data["metric_key"],
                data["interface_name"],
                data["value"],
                ts_collected,
            )
        
        # Publish to bus for real-time UI (throttled)
        self._publish_to_bus(env, device, metrics, ts_collected)
        
        return len(points)

    def _publish_to_bus(self, env, device, metrics, ts_collected):
        """Publish latest snapshot to Odoo bus for real-time UI."""
        channel = f"mikrotik_monitoring.device.{device.id}"
        
        payload = {
            "device_id": device.id,
            "device_uid": device.device_uid,
            "ts": ts_collected.isoformat(),
            "metrics": metrics,
        }
        
        env["bus.bus"]._sendone(channel, "mikrotik_update", payload)

    @http.route(
        "/mikrotik/ingest/events",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def ingest_events(self, collector_id=None, signature=None, timestamp=None, events=None, **kwargs):
        """Ingest events from collector.
        
        Expected payload:
        {
            "collector_id": "collector-01",
            "signature": "hmac-sha256-hex",
            "events": [
                {
                    "device_uid": "MT-0001",
                    "ts": "2026-01-05T10:00:01Z",
                    "event_type": "interface_down",
                    "severity": "warning",
                    "subject": "ether1",
                    "message": "Interface went down",
                    "data": {...}
                }
            ]
        }
        """
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            if not self._validate_signature(data):
                return {"success": False, "error": "Authentication failed"}
            
            events_data = events or []
            env = request.env(user=SUPERUSER_ID)
            
            Device = env["mikrotik.device"]
            Event = env["mikrotik.event"]
            
            created = 0
            for event_data in events_data:
                device_uid = event_data.get("device_uid")
                device = Device.search([("device_uid", "=", device_uid)], limit=1)
                
                if not device:
                    continue
                
                Event.log_event(
                    device_id=device.id,
                    event_type=event_data.get("event_type", "info"),
                    subject=event_data.get("subject"),
                    message=event_data.get("message"),
                    severity=event_data.get("severity", "info"),
                    data=event_data.get("data"),
                )
                created += 1
            
            return {"success": True, "events_created": created}
            
        except Exception as e:
            _logger.exception("Event ingest error")
            return {"success": False, "error": str(e)}

    @http.route(
        "/mikrotik/ingest/interfaces",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def ingest_interfaces(self, collector_id=None, signature=None, timestamp=None, device_uid=None, interfaces=None, **kwargs):
        """Ingest interface inventory from collector."""
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            if not self._validate_signature(data):
                return {"success": False, "error": "Authentication failed"}
            
            env = request.env(user=SUPERUSER_ID)
            Device = env["mikrotik.device"]
            Interface = env["mikrotik.interface"]
            
            interfaces_data = interfaces or []
            
            device = Device.search([("device_uid", "=", device_uid)], limit=1)
            if not device:
                return {"success": False, "error": "Unknown device"}
            
            Interface.sync_from_router(device.id, interfaces_data)
            
            return {"success": True, "interfaces_synced": len(interfaces_data)}
            
        except Exception as e:
            _logger.exception("Interface ingest error")
            return {"success": False, "error": str(e)}

    @http.route(
        "/mikrotik/ingest/leases",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def ingest_leases(self, collector_id=None, signature=None, timestamp=None, device_uid=None, leases=None, **kwargs):
        """Ingest DHCP leases from collector."""
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            if not self._validate_signature(data):
                return {"success": False, "error": "Authentication failed"}
            
            env = request.env(user=SUPERUSER_ID)
            Device = env["mikrotik.device"]
            Lease = env["mikrotik.lease"]
            
            leases_data = leases or []
            
            device = Device.search([("device_uid", "=", device_uid)], limit=1)
            if not device:
                return {"success": False, "error": "Unknown device"}
            
            Lease.sync_leases(device.id, leases_data)
            
            # Log aggregate to metrics
            MetricLatest = env["mikrotik.metric.latest"]
            MetricLatest._upsert_single(
                device.id,
                "dhcp.active_leases",
                None,
                len([l for l in leases_data if l.get("status") != "expired"]),
                fields.Datetime.now(),
            )
            
            return {"success": True, "leases_synced": len(leases_data)}
            
        except Exception as e:
            _logger.exception("Lease ingest error")
            return {"success": False, "error": str(e)}

    @http.route(
        "/mikrotik/ingest/sessions",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def ingest_sessions(self, collector_id=None, signature=None, timestamp=None, device_uid=None, session_type=None, sessions=None, **kwargs):
        """Ingest PPPoE/Hotspot sessions from collector."""
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            if not self._validate_signature(data):
                return {"success": False, "error": "Authentication failed"}
            
            env = request.env(user=SUPERUSER_ID)
            Device = env["mikrotik.device"]
            Session = env["mikrotik.session"]
            
            session_type = session_type or "pppoe"
            sessions_data = sessions or []
            
            device = Device.search([("device_uid", "=", device_uid)], limit=1)
            if not device:
                return {"success": False, "error": "Unknown device"}
            
            Session.sync_sessions(device.id, session_type, sessions_data)
            
            # Log aggregate to metrics
            MetricLatest = env["mikrotik.metric.latest"]
            metric_key = "ppp.active_sessions" if session_type == "pppoe" else "hotspot.active_users"
            MetricLatest._upsert_single(
                device.id,
                metric_key,
                None,
                len([s for s in sessions_data]),
                fields.Datetime.now(),
            )
            
            return {"success": True, "sessions_synced": len(sessions_data)}
            
        except Exception as e:
            _logger.exception("Session ingest error")
            return {"success": False, "error": str(e)}
