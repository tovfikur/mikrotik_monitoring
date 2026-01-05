# -*- coding: utf-8 -*-

import logging
from odoo import http, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class MikrotikApiController(http.Controller):
    """API endpoints for collector to fetch device configuration."""

    @http.route(
        "/mikrotik/api/devices",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def get_devices(self, collector_id=None, secret=None, signature=None, timestamp=None, **kwargs):
        """Get list of devices for collector to poll.
        
        Returns device configuration including credentials.
        Must be authenticated.
        """
        try:
            data = {
                "collector_id": collector_id,
                "secret": secret,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            # Validate collector
            if not self._validate_collector(data):
                return {"success": False, "error": "Authentication failed"}
            
            env = request.env(user=SUPERUSER_ID)
            Device = env["mikrotik.device"]
            
            devices = Device.get_device_config_for_collector()
            
            return {
                "success": True,
                "devices": devices,
            }
            
        except Exception as e:
            _logger.exception("API error")
            return {"success": False, "error": str(e)}

    @http.route(
        "/mikrotik/api/device/<string:device_uid>/capabilities",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def update_capabilities(self, device_uid, collector_id=None, signature=None, timestamp=None, capabilities=None, **kwargs):
        """Update device capabilities from collector discovery."""
        try:
            data = {
                "collector_id": collector_id,
                "signature": signature,
                "timestamp": timestamp,
            }
            
            if not self._validate_collector(data):
                return {"success": False, "error": "Authentication failed"}
            
            env = request.env(user=SUPERUSER_ID)
            Device = env["mikrotik.device"]
            Capability = env["mikrotik.device.capability"]
            
            device = Device.search([("device_uid", "=", device_uid)], limit=1)
            if not device:
                return {"success": False, "error": "Unknown device"}
            
            caps = capabilities or {}
            
            vals = {
                "device_id": device.id,
                "routeros_version": caps.get("version", ""),
                "routeros_major": int(caps.get("version", "7").split(".")[0]),
                "board_name": caps.get("board-name", ""),
                "architecture": caps.get("architecture-name", ""),
                "identity": caps.get("identity", ""),
                "serial_number": caps.get("serial-number", ""),
                "cpu_count": int(caps.get("cpu-count", 1)),
                "total_memory": int(caps.get("total-memory", 0)),
                "total_disk": int(caps.get("total-hdd-space", 0)),
                "supports_rest": caps.get("supports_rest", False),
                "has_wireless": caps.get("has_wireless", False),
                "wifi_mode": caps.get("wifi_mode", "none"),
                "has_lte": caps.get("has_lte", False),
                "has_mpls": caps.get("has_mpls", False),
                "has_container": caps.get("has_container", False),
                "has_bgp": caps.get("has_bgp", False),
                "has_ospf": caps.get("has_ospf", False),
                "has_ppp": caps.get("has_ppp", True),
                "has_hotspot": caps.get("has_hotspot", False),
                "has_dhcp_server": caps.get("has_dhcp_server", True),
                "has_gps": caps.get("has_gps", False),
            }
            
            if device.capability_id:
                device.capability_id.write(vals)
            else:
                cap = Capability.create(vals)
                device.capability_id = cap.id
            
            return {"success": True}
            
        except Exception as e:
            _logger.exception("Capability update error")
            return {"success": False, "error": str(e)}

    @http.route(
        "/mikrotik/api/health",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def health_check(self, **kwargs):
        """Simple health check endpoint."""
        return "OK"

    def _validate_collector(self, data):
        """Validate collector authentication."""
        import hmac
        import hashlib
        
        IrParam = request.env["ir.config_parameter"].sudo()
        secret = IrParam.get_param("mikrotik_monitoring.collector_secret", "")
        
        if not secret:
            return True
        
        signature = data.get("signature", "")
        if not signature:
            return False
        
        collector_id = data.get("collector_id", "")
        timestamp = data.get("timestamp", "")
        message = f"{collector_id}:{timestamp}"
        
        expected = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
