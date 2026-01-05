# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class MikrotikMetricPoint(models.Model):
    """Time-series telemetry storage - append-only, partitioned by day.
    
    This table stores raw 1-second telemetry for T0 metrics.
    For ISP-grade performance:
    - Use numeric metric_id instead of text key
    - Partition by ts_collected (daily)
    - Minimal indexes on raw table
    - Use BRIN index for time-range scans
    """

    _name = "mikrotik.metric.point"
    _description = "MikroTik Metric Point"
    _order = "ts_collected DESC"
    _log_access = False  # Disable tracking for high-volume writes

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    metric_id = fields.Many2one(
        "mikrotik.metric.catalog",
        string="Metric",
        required=True,
        index=True,
        ondelete="cascade",
    )
    interface_name = fields.Char(
        string="Interface",
        index=True,
        help="Interface name for interface-level metrics (null for system metrics)",
    )
    
    ts_collected = fields.Datetime(
        string="Timestamp (Collected)",
        required=True,
        index=True,
        help="Timestamp when the metric was collected from the router",
    )
    ts_received = fields.Datetime(
        string="Timestamp (Received)",
        default=fields.Datetime.now,
        help="Timestamp when the metric was received by Odoo",
    )
    
    value_float = fields.Float(
        string="Value (Numeric)",
        digits=(20, 4),
    )
    value_text = fields.Char(
        string="Value (Text)",
        help="For non-numeric metrics (rare)",
    )

    @api.model
    def _auto_init(self):
        """Create optimized indexes after table creation."""
        res = super()._auto_init()
        tools.create_index(
            self._cr,
            "mikrotik_metric_point_device_ts_idx",
            self._table,
            ["device_id", "ts_collected DESC"],
        )
        return res

    @api.model
    def bulk_create(self, points):
        """High-performance bulk insert using raw SQL.
        
        Args:
            points: list of dicts with keys:
                device_id, metric_id, interface_name, ts_collected, value_float, value_text
        
        Returns:
            Number of points inserted
        """
        if not points:
            return 0
        
        # Build values for INSERT
        values = []
        for p in points:
            values.append((
                p.get("device_id"),
                p.get("metric_id"),
                p.get("interface_name"),
                p.get("ts_collected"),
                fields.Datetime.now(),
                p.get("value_float"),
                p.get("value_text"),
            ))
        
        # Use executemany for efficiency
        query = """
            INSERT INTO mikrotik_metric_point 
            (device_id, metric_id, interface_name, ts_collected, ts_received, value_float, value_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self._cr.executemany(query, values)
        
        return len(values)

    @api.model
    def cleanup_old_partitions(self, retention_days=90):
        """Delete metrics older than retention period.
        
        For ISP-grade: this should be done via partition DROP, not DELETE.
        This method is a fallback for non-partitioned setups.
        """
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # Use raw SQL for efficiency
        query = """
            DELETE FROM mikrotik_metric_point 
            WHERE ts_collected < %s
        """
        self._cr.execute(query, (cutoff,))
        deleted = self._cr.rowcount
        
        if deleted:
            _logger.info("Deleted %d old metric points (retention=%d days)", deleted, retention_days)
        
        return deleted
