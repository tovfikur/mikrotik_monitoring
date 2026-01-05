# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikDeviceCapability(models.Model):
    """Device capabilities discovered from RouterOS."""

    _name = "mikrotik.device.capability"
    _description = "MikroTik Device Capability"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        ondelete="cascade",
        index=True,
    )
    
    # Version info
    routeros_version = fields.Char(string="RouterOS Version")
    routeros_major = fields.Integer(string="Major Version", default=7)
    
    # Hardware info
    board_name = fields.Char(string="Board Name")
    architecture = fields.Char(string="Architecture")
    identity = fields.Char(string="Identity")
    serial_number = fields.Char(string="Serial Number")
    cpu_count = fields.Integer(string="CPU Count", default=1)
    total_memory = fields.Integer(string="Total Memory (bytes)")
    total_disk = fields.Integer(string="Total Disk (bytes)")
    
    # Feature flags
    supports_rest = fields.Boolean(string="Supports REST API", default=False)
    has_wireless = fields.Boolean(string="Has Wireless", default=False)
    wifi_mode = fields.Selection(
        [
            ("none", "None"),
            ("legacy", "Legacy Wireless"),
            ("wifiwave2", "WiFiWave2"),
        ],
        string="WiFi Mode",
        default="none",
    )
    has_lte = fields.Boolean(string="Has LTE", default=False)
    has_mpls = fields.Boolean(string="Has MPLS", default=False)
    has_container = fields.Boolean(string="Has Container", default=False)
    has_ipv6 = fields.Boolean(string="Has IPv6", default=True)
    has_bgp = fields.Boolean(string="Has BGP", default=False)
    has_ospf = fields.Boolean(string="Has OSPF", default=False)
    has_ppp = fields.Boolean(string="Has PPP", default=True)
    has_hotspot = fields.Boolean(string="Has Hotspot", default=False)
    has_dhcp_server = fields.Boolean(string="Has DHCP Server", default=True)
    has_gps = fields.Boolean(string="Has GPS", default=False)
    
    # Package list (JSON)
    packages_json = fields.Text(string="Packages (JSON)")
    
    # Refresh tracking
    last_refresh = fields.Datetime(string="Last Refresh")

    def get_feature_flags(self):
        """Return a dict of feature flags for collector use."""
        self.ensure_one()
        return {
            "routeros_major": self.routeros_major,
            "supports_rest": self.supports_rest,
            "wifi_mode": self.wifi_mode,
            "has_lte": self.has_lte,
            "has_mpls": self.has_mpls,
            "has_container": self.has_container,
            "has_ipv6": self.has_ipv6,
            "has_bgp": self.has_bgp,
            "has_ospf": self.has_ospf,
            "has_ppp": self.has_ppp,
            "has_hotspot": self.has_hotspot,
            "has_dhcp_server": self.has_dhcp_server,
            "has_gps": self.has_gps,
        }
