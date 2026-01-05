# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikMetricCatalog(models.Model):
    """Metric catalog - defines all known metric keys and their properties."""

    _name = "mikrotik.metric.catalog"
    _description = "MikroTik Metric Catalog"
    _order = "key"

    key = fields.Char(
        string="Metric Key",
        required=True,
        index=True,
        help="Normalized metric key (e.g., system.cpu.load_pct)",
    )
    name = fields.Char(
        string="Display Name",
        required=True,
    )
    description = fields.Text(string="Description")
    
    unit = fields.Selection(
        [
            ("bytes", "Bytes"),
            ("bps", "Bits per second"),
            ("pps", "Packets per second"),
            ("percent", "Percent"),
            ("count", "Count"),
            ("seconds", "Seconds"),
            ("celsius", "Celsius"),
            ("dbm", "dBm"),
            ("text", "Text"),
        ],
        string="Unit",
        default="count",
    )
    metric_type = fields.Selection(
        [
            ("gauge", "Gauge"),
            ("counter", "Counter"),
        ],
        string="Type",
        default="gauge",
        help="Gauge: point-in-time value. Counter: cumulative, use for rate calc.",
    )
    collection_tier = fields.Selection(
        [
            ("t0", "T0 (1s)"),
            ("t1", "T1 (10s)"),
            ("t2", "T2 (60s)"),
            ("t3", "T3 (15m+)"),
        ],
        string="Collection Tier",
        default="t0",
    )
    
    # Validation
    expected_min = fields.Float(string="Expected Min", default=0)
    expected_max = fields.Float(string="Expected Max", default=0)
    
    # Categorization
    category = fields.Selection(
        [
            ("system", "System"),
            ("interface", "Interface"),
            ("routing", "Routing"),
            ("firewall", "Firewall"),
            ("wireless", "Wireless"),
            ("lte", "LTE"),
            ("dhcp", "DHCP"),
            ("ppp", "PPP/Hotspot"),
            ("queue", "Queue/QoS"),
            ("other", "Other"),
        ],
        string="Category",
        default="other",
    )
    
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("key_uniq", "UNIQUE(key)", "Metric key must be unique."),
    ]

    @api.model
    def get_metric_id(self, key):
        """Get or create metric catalog entry, return ID."""
        metric = self.search([("key", "=", key)], limit=1)
        if metric:
            return metric.id
        # Auto-create with defaults
        return self.create({
            "key": key,
            "name": key.replace(".", " ").replace("_", " ").title(),
        }).id

    @api.model
    def init_default_metrics(self):
        """Initialize default metric catalog entries."""
        defaults = [
            # System metrics
            {"key": "system.cpu.load_pct", "name": "CPU Load %", "unit": "percent", "category": "system"},
            {"key": "system.mem.used_bytes", "name": "Memory Used", "unit": "bytes", "category": "system"},
            {"key": "system.mem.free_bytes", "name": "Memory Free", "unit": "bytes", "category": "system"},
            {"key": "system.disk.free_bytes", "name": "Disk Free", "unit": "bytes", "category": "system"},
            {"key": "system.uptime_sec", "name": "Uptime", "unit": "seconds", "category": "system"},
            {"key": "system.temperature", "name": "Temperature", "unit": "celsius", "category": "system"},
            
            # Interface counters
            {"key": "iface.rx_bytes_total", "name": "RX Bytes Total", "unit": "bytes", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_bytes_total", "name": "TX Bytes Total", "unit": "bytes", "metric_type": "counter", "category": "interface"},
            {"key": "iface.rx_packets_total", "name": "RX Packets Total", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_packets_total", "name": "TX Packets Total", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.rx_bps", "name": "RX Rate", "unit": "bps", "category": "interface"},
            {"key": "iface.tx_bps", "name": "TX Rate", "unit": "bps", "category": "interface"},
            {"key": "iface.rx_errors", "name": "RX Errors", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_errors", "name": "TX Errors", "unit": "count", "metric_type": "counter", "category": "interface"},
            
            # Firewall/conntrack
            {"key": "firewall.conntrack_count", "name": "Conntrack Entries", "unit": "count", "category": "firewall"},
            
            # Wireless
            {"key": "wireless.client_count", "name": "Wireless Clients", "unit": "count", "category": "wireless"},
            
            # LTE
            {"key": "lte.rsrp", "name": "LTE RSRP", "unit": "dbm", "category": "lte"},
            {"key": "lte.rsrq", "name": "LTE RSRQ", "unit": "dbm", "category": "lte"},
            {"key": "lte.sinr", "name": "LTE SINR", "unit": "dbm", "category": "lte"},
            
            # DHCP
            {"key": "dhcp.active_leases", "name": "Active DHCP Leases", "unit": "count", "category": "dhcp"},
            
            # PPP/Hotspot
            {"key": "ppp.active_sessions", "name": "Active PPP Sessions", "unit": "count", "category": "ppp"},
            {"key": "hotspot.active_users", "name": "Active Hotspot Users", "unit": "count", "category": "ppp"},
        ]
        
        for metric_vals in defaults:
            existing = self.search([("key", "=", metric_vals["key"])], limit=1)
            if not existing:
                self.create(metric_vals)
