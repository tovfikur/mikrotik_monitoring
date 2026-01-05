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
            {"key": "system.memory.used_pct", "name": "Memory Used %", "unit": "percent", "category": "system"},
            {"key": "system.memory.free_bytes", "name": "Memory Free", "unit": "bytes", "category": "system"},
            {"key": "system.memory.total_bytes", "name": "Memory Total", "unit": "bytes", "category": "system"},
            {"key": "system.disk.used_pct", "name": "Disk Used %", "unit": "percent", "category": "system"},
            {"key": "system.disk.free_bytes", "name": "Disk Free", "unit": "bytes", "category": "system"},
            {"key": "system.uptime_seconds", "name": "Uptime", "unit": "seconds", "category": "system"},
            {"key": "system.temperature", "name": "Temperature", "unit": "celsius", "category": "system"},
            
            # System health metrics
            {"key": "system.health.temperature", "name": "Temperature", "unit": "celsius", "category": "system"},
            {"key": "system.health.voltage", "name": "Voltage", "unit": "text", "category": "system"},
            {"key": "system.health.fan1-speed", "name": "Fan 1 Speed", "unit": "text", "category": "system"},
            {"key": "system.health.fan2-speed", "name": "Fan 2 Speed", "unit": "text", "category": "system"},
            {"key": "system.health.psu1-voltage", "name": "PSU 1 Voltage", "unit": "text", "category": "system"},
            {"key": "system.health.psu2-voltage", "name": "PSU 2 Voltage", "unit": "text", "category": "system"},
            
            # Interface traffic rates
            {"key": "iface.rx_bps", "name": "RX Rate (bps)", "unit": "bps", "category": "interface"},
            {"key": "iface.tx_bps", "name": "TX Rate (bps)", "unit": "bps", "category": "interface"},
            
            # Interface errors and drops
            {"key": "iface.rx_error", "name": "RX Errors", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_error", "name": "TX Errors", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.rx_drop", "name": "RX Drops", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_drop", "name": "TX Drops", "unit": "count", "metric_type": "counter", "category": "interface"},
            
            # Interface counters
            {"key": "iface.rx_bytes_total", "name": "RX Bytes Total", "unit": "bytes", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_bytes_total", "name": "TX Bytes Total", "unit": "bytes", "metric_type": "counter", "category": "interface"},
            {"key": "iface.rx_packets_total", "name": "RX Packets Total", "unit": "count", "metric_type": "counter", "category": "interface"},
            {"key": "iface.tx_packets_total", "name": "TX Packets Total", "unit": "count", "metric_type": "counter", "category": "interface"},
            
            # Firewall/conntrack
            {"key": "firewall.connection_count", "name": "Active Connections", "unit": "count", "category": "firewall"},
            {"key": "firewall.drops_total", "name": "Firewall Drops", "unit": "count", "metric_type": "counter", "category": "firewall"},
            {"key": "firewall.drops_bytes", "name": "Firewall Drop Bytes", "unit": "bytes", "metric_type": "counter", "category": "firewall"},
            
            # Queue/Bandwidth
            {"key": "queue.current_rate", "name": "Queue Current Rate", "unit": "bps", "category": "queue"},
            {"key": "queue.max_limit", "name": "Queue Max Limit", "unit": "bps", "category": "queue"},
            
            # Latency and packet loss
            {"key": "ping.avg_latency_ms", "name": "Ping Avg Latency", "unit": "seconds", "category": "system"},
            {"key": "ping.max_latency_ms", "name": "Ping Max Latency", "unit": "seconds", "category": "system"},
            {"key": "ping.packet_loss_pct", "name": "Ping Packet Loss", "unit": "percent", "category": "system"},
            
            # BGP
            {"key": "bgp.prefix_count", "name": "BGP Prefix Count", "unit": "count", "category": "routing"},
            {"key": "bgp.session_state", "name": "BGP Session State", "unit": "text", "category": "routing"},
            
            # Routing
            {"key": "routing.route_count", "name": "Route Count", "unit": "count", "category": "routing"},
            
            # Wireless
            {"key": "wireless.client_count", "name": "Wireless Clients", "unit": "count", "category": "wireless"},
            
            # LTE
            {"key": "lte.rsrp", "name": "LTE RSRP", "unit": "dbm", "category": "lte"},
            {"key": "lte.rsrq", "name": "LTE RSRQ", "unit": "dbm", "category": "lte"},
            {"key": "lte.sinr", "name": "LTE SINR", "unit": "dbm", "category": "lte"},
            
            # DHCP
            {"key": "dhcp.active_leases", "name": "Active DHCP Leases", "unit": "count", "category": "dhcp"},
            {"key": "dhcp.total_leases", "name": "Total DHCP Leases", "unit": "count", "category": "dhcp"},
            
            # PPP/Hotspot
            {"key": "ppp.active_sessions", "name": "Active PPP Sessions", "unit": "count", "category": "ppp"},
            {"key": "hotspot.active_users", "name": "Active Hotspot Users", "unit": "count", "category": "ppp"},
        ]
        
        for metric_vals in defaults:
            existing = self.search([("key", "=", metric_vals["key"])], limit=1)
            if not existing:
                self.create(metric_vals)
