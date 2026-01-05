# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikEvent(models.Model):
    """Events and state changes from devices.
    
    Used for:
    - Interface state changes (up/down)
    - Routing neighbor changes (BGP/OSPF)
    - Login failures
    - DHCP lease events
    - Device connectivity events
    """

    _name = "mikrotik.event"
    _description = "MikroTik Event"
    _order = "ts DESC"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    
    ts = fields.Datetime(
        string="Timestamp",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    
    event_type = fields.Selection(
        [
            ("device_up", "Device Up"),
            ("device_down", "Device Down"),
            ("device_degraded", "Device Degraded"),
            ("interface_up", "Interface Up"),
            ("interface_down", "Interface Down"),
            ("bgp_established", "BGP Established"),
            ("bgp_down", "BGP Down"),
            ("ospf_full", "OSPF Full"),
            ("ospf_down", "OSPF Down"),
            ("ppp_connect", "PPP Connect"),
            ("ppp_disconnect", "PPP Disconnect"),
            ("hotspot_login", "Hotspot Login"),
            ("hotspot_logout", "Hotspot Logout"),
            ("dhcp_lease", "DHCP Lease"),
            ("dhcp_expire", "DHCP Expire"),
            ("login_failure", "Login Failure"),
            ("config_change", "Config Change"),
            ("reboot", "Device Reboot"),
            ("error", "Error"),
            ("warning", "Warning"),
            ("info", "Info"),
        ],
        string="Event Type",
        required=True,
        index=True,
    )
    
    severity = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        string="Severity",
        default="info",
        index=True,
    )
    
    subject = fields.Char(
        string="Subject",
        index=True,
        help="Interface name, BGP peer, user, etc.",
    )
    message = fields.Text(
        string="Message",
    )
    data_json = fields.Text(
        string="Data (JSON)",
        help="Additional structured data",
    )
    
    # For correlation
    source = fields.Char(
        string="Source",
        help="Collector ID, syslog, API, etc.",
    )

    @api.model
    def log_event(self, device_id, event_type, subject=None, message=None, severity="info", data=None):
        """Create an event log entry."""
        import json
        return self.create({
            "device_id": device_id,
            "event_type": event_type,
            "severity": severity,
            "subject": subject,
            "message": message,
            "data_json": json.dumps(data) if data else None,
        })

    @api.model
    def cleanup_old_events(self, retention_days=180):
        """Delete events older than retention period."""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        old_events = self.search([("ts", "<", cutoff)])
        count = len(old_events)
        old_events.unlink()
        
        return count
