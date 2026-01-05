# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MikrotikMetricLatest(models.Model):
    """Latest metric values per device - for fast UI reads.
    
    This table is updated via UPSERT on each ingestion cycle.
    It provides instant access to current values without scanning
    the large time-series table.
    """

    _name = "mikrotik.metric.latest"
    _description = "MikroTik Latest Metric"
    _order = "device_id, metric_key"
    _rec_name = "metric_key"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    metric_key = fields.Char(
        string="Metric Key",
        required=True,
        index=True,
    )
    interface_name = fields.Char(
        string="Interface",
        index=True,
    )
    
    ts_collected = fields.Datetime(
        string="Timestamp",
        required=True,
        index=True,
    )
    
    value_float = fields.Float(
        string="Value (Numeric)",
        digits=(20, 4),
    )
    value_text = fields.Char(
        string="Value (Text)",
    )
    
    # Computed display
    display_value = fields.Char(
        string="Value",
        compute="_compute_display_value",
    )
    
    # For rate metrics, store previous value to compute delta
    prev_value = fields.Float(
        string="Previous Value",
        digits=(20, 4),
    )
    prev_ts = fields.Datetime(
        string="Previous Timestamp",
    )

    _sql_constraints = [
        (
            "device_metric_interface_uniq",
            "UNIQUE(device_id, metric_key, interface_name)",
            "Metric key must be unique per device/interface.",
        ),
    ]

    def _compute_display_value(self):
        for rec in self:
            if rec.value_text:
                rec.display_value = rec.value_text
            elif rec.value_float is not None:
                # Format based on metric type
                if "bps" in rec.metric_key:
                    rec.display_value = self._format_bps(rec.value_float)
                elif "bytes" in rec.metric_key:
                    rec.display_value = self._format_bytes(rec.value_float)
                elif "pct" in rec.metric_key or "percent" in rec.metric_key:
                    rec.display_value = f"{rec.value_float:.1f}%"
                else:
                    rec.display_value = f"{rec.value_float:,.2f}"
            else:
                rec.display_value = "-"

    @staticmethod
    def _format_bytes(value):
        """Format bytes to human readable."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(value) < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"

    @staticmethod
    def _format_bps(value):
        """Format bits per second to human readable."""
        for unit in ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]:
            if abs(value) < 1000.0:
                return f"{value:.1f} {unit}"
            value /= 1000.0
        return f"{value:.1f} Pbps"

    @api.model
    def upsert_metrics(self, device_id, metrics, ts_collected):
        """Upsert multiple metrics for a device.
        
        Args:
            device_id: ID of the device
            metrics: dict of {metric_key: value} or {metric_key: {interface: value}}
            ts_collected: datetime of collection
        """
        for metric_key, value in metrics.items():
            if isinstance(value, dict):
                # Interface-level metrics
                for iface_name, iface_value in value.items():
                    self._upsert_single(device_id, metric_key, iface_name, iface_value, ts_collected)
            else:
                # Device-level metrics
                self._upsert_single(device_id, metric_key, None, value, ts_collected)

    def _upsert_single(self, device_id, metric_key, interface_name, value, ts_collected):
        """Upsert a single metric value."""
        # Determine value type
        if isinstance(value, str):
            value_float = None
            value_text = value
        else:
            value_float = float(value) if value is not None else None
            value_text = None
        
        # Handle null interface_name for SQL
        iface_sql = interface_name if interface_name else ""
        
        # Try to find existing record
        domain = [
            ("device_id", "=", device_id),
            ("metric_key", "=", metric_key),
        ]
        if interface_name:
            domain.append(("interface_name", "=", interface_name))
        else:
            domain.append("|")
            domain.append(("interface_name", "=", False))
            domain.append(("interface_name", "=", ""))
        
        existing = self.search(domain, limit=1)
        
        if existing:
            # Store previous for rate calculation
            existing.write({
                "prev_value": existing.value_float,
                "prev_ts": existing.ts_collected,
                "value_float": value_float,
                "value_text": value_text,
                "ts_collected": ts_collected,
            })
        else:
            self.create({
                "device_id": device_id,
                "metric_key": metric_key,
                "interface_name": interface_name or False,
                "value_float": value_float,
                "value_text": value_text,
                "ts_collected": ts_collected,
            })

    @api.model
    def get_device_snapshot(self, device_id):
        """Get all latest metrics for a device as a dict."""
        metrics = self.search([("device_id", "=", device_id)])
        result = {}
        for m in metrics:
            key = m.metric_key
            if m.interface_name:
                key = f"{key}.{m.interface_name}"
            result[key] = {
                "value": m.value_float if m.value_float is not None else m.value_text,
                "display": m.display_value,
                "ts": m.ts_collected.isoformat() if m.ts_collected else None,
            }
        return result
