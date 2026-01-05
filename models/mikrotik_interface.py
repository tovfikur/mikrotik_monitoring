# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikInterface(models.Model):
    """Router interface inventory and current state."""

    _name = "mikrotik.interface"
    _description = "MikroTik Interface"
    _order = "device_id, name"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    
    name = fields.Char(
        string="Name",
        required=True,
        index=True,
    )
    interface_type = fields.Selection(
        [
            ("ether", "Ethernet"),
            ("wlan", "Wireless"),
            ("bridge", "Bridge"),
            ("vlan", "VLAN"),
            ("bond", "Bonding"),
            ("pppoe-client", "PPPoE Client"),
            ("pppoe-server", "PPPoE Server"),
            ("l2tp", "L2TP"),
            ("sstp", "SSTP"),
            ("ovpn", "OpenVPN"),
            ("wireguard", "WireGuard"),
            ("gre", "GRE"),
            ("eoip", "EoIP"),
            ("vxlan", "VXLAN"),
            ("lte", "LTE"),
            ("sfp", "SFP"),
            ("sfp-sfpplus", "SFP+"),
            ("loopback", "Loopback"),
            ("other", "Other"),
        ],
        string="Type",
        default="other",
    )
    
    # State
    is_enabled = fields.Boolean(string="Enabled", default=True)
    is_running = fields.Boolean(string="Running", default=False)
    last_link_up = fields.Datetime(string="Last Link Up")
    last_link_down = fields.Datetime(string="Last Link Down")
    
    # Properties
    mac_address = fields.Char(string="MAC Address")
    mtu = fields.Integer(string="MTU", default=1500)
    speed = fields.Char(string="Speed")
    duplex = fields.Selection(
        [("full", "Full"), ("half", "Half")],
        string="Duplex",
    )
    
    # Classification
    is_uplink = fields.Boolean(
        string="Is Uplink",
        help="Marked as uplink interface (always T0)",
    )
    is_sla = fields.Boolean(
        string="SLA Interface",
        help="Business-critical interface (always T0)",
    )
    t0_enabled = fields.Boolean(
        string="T0 Enabled",
        help="Enable 1-second polling for this interface",
        default=False,
    )
    collection_tier = fields.Selection(
        [
            ("t0", "T0 (1s)"),
            ("t1", "T1 (10s)"),
            ("t2", "T2 (60s)"),
            ("auto", "Auto"),
        ],
        string="Collection Tier",
        default="auto",
        help="Override automatic tier selection",
    )
    
    # Latest traffic stats (from mikrotik.metric.latest)
    rx_bps = fields.Float(
        string="RX Rate (bps)",
        compute="_compute_traffic",
    )
    tx_bps = fields.Float(
        string="TX Rate (bps)",
        compute="_compute_traffic",
    )
    rx_bps_display = fields.Char(
        string="RX Rate",
        compute="_compute_traffic",
    )
    tx_bps_display = fields.Char(
        string="TX Rate",
        compute="_compute_traffic",
    )
    last_seen = fields.Datetime(
        string="Last Seen",
        help="Last time data was collected from this interface",
    )

    _sql_constraints = [
        (
            "device_name_uniq",
            "UNIQUE(device_id, name)",
            "Interface name must be unique per device.",
        ),
    ]

    def _compute_traffic(self):
        MetricLatest = self.env["mikrotik.metric.latest"]
        for iface in self:
            rx_metric = MetricLatest.search([
                ("device_id", "=", iface.device_id.id),
                ("metric_key", "=", "iface.rx_bps"),
                ("interface_name", "=", iface.name),
            ], limit=1)
            tx_metric = MetricLatest.search([
                ("device_id", "=", iface.device_id.id),
                ("metric_key", "=", "iface.tx_bps"),
                ("interface_name", "=", iface.name),
            ], limit=1)
            
            iface.rx_bps = rx_metric.value_float if rx_metric else 0
            iface.tx_bps = tx_metric.value_float if tx_metric else 0
            iface.rx_bps_display = MetricLatest._format_bps(iface.rx_bps)
            iface.tx_bps_display = MetricLatest._format_bps(iface.tx_bps)

    @api.model
    def sync_from_router(self, device_id, interfaces_data):
        """Sync interface inventory from router data.
        
        Args:
            device_id: ID of the device
            interfaces_data: list of dicts with interface info from RouterOS
        """
        existing = {i.name: i for i in self.search([("device_id", "=", device_id)])}
        
        seen_names = set()
        for iface_data in interfaces_data:
            name = iface_data.get("name")
            if not name:
                continue
            seen_names.add(name)
            
            # Handle both collector format and raw RouterOS format
            is_enabled = iface_data.get("is_enabled")
            if is_enabled is None:
                is_enabled = not iface_data.get("disabled", False)
            
            is_running = iface_data.get("is_running")
            if is_running is None:
                is_running = iface_data.get("running", False)
            
            mac_address = iface_data.get("mac_address") or iface_data.get("mac-address")
            
            # Parse MTU safely
            mtu_raw = iface_data.get("mtu", 1500)
            try:
                mtu = int(mtu_raw) if mtu_raw and str(mtu_raw).isdigit() else 1500
            except (ValueError, TypeError):
                mtu = 1500
            
            vals = {
                "device_id": device_id,
                "name": name,
                "interface_type": self._detect_type(iface_data.get("type", "")),
                "is_enabled": bool(is_enabled),
                "is_running": bool(is_running),
                "mac_address": mac_address,
                "mtu": mtu,
            }
            
            if name in existing:
                existing[name].write(vals)
            else:
                self.create(vals)
        
        # Mark interfaces not seen as disabled (don't delete to preserve history)
        for name, iface in existing.items():
            if name not in seen_names:
                iface.is_enabled = False
                iface.is_running = False

    def _detect_type(self, ros_type):
        """Map RouterOS type to our selection."""
        type_map = {
            "ether": "ether",
            "wlan": "wlan",
            "bridge": "bridge",
            "vlan": "vlan",
            "bonding": "bond",
            "pppoe-out": "pppoe-client",
            "pppoe-in": "pppoe-server",
            "l2tp-out": "l2tp",
            "l2tp-in": "l2tp",
            "sstp-out": "sstp",
            "sstp-in": "sstp",
            "ovpn-out": "ovpn",
            "ovpn-in": "ovpn",
            "wireguard": "wireguard",
            "gre-tunnel": "gre",
            "eoip-tunnel": "eoip",
            "vxlan": "vxlan",
            "lte": "lte",
        }
        return type_map.get(ros_type, "other")
