# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikSession(models.Model):
    """PPPoE/Hotspot/VPN session current state table.
    
    For high user counts, this stores current state (upserted),
    not time-series. Use mikrotik.event for session events.
    """

    _name = "mikrotik.session"
    _description = "MikroTik Session"
    _order = "device_id, started_at DESC"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    
    session_type = fields.Selection(
        [
            ("pppoe", "PPPoE"),
            ("pptp", "PPTP"),
            ("l2tp", "L2TP"),
            ("sstp", "SSTP"),
            ("ovpn", "OpenVPN"),
            ("hotspot", "Hotspot"),
            ("wireguard", "WireGuard"),
        ],
        string="Type",
        required=True,
        index=True,
    )
    
    name = fields.Char(
        string="Username",
        index=True,
    )
    address = fields.Char(
        string="IP Address",
        index=True,
    )
    caller_id = fields.Char(
        string="Caller ID / MAC",
    )
    
    service = fields.Char(
        string="Service / Profile",
    )
    interface = fields.Char(
        string="Interface",
    )
    
    started_at = fields.Datetime(
        string="Started At",
        default=fields.Datetime.now,
    )
    uptime = fields.Integer(
        string="Uptime (seconds)",
    )
    uptime_display = fields.Char(
        string="Uptime",
        compute="_compute_uptime_display",
    )
    
    # Traffic
    bytes_in = fields.Float(string="Bytes In")
    bytes_out = fields.Float(string="Bytes Out")
    
    # Status
    is_active = fields.Boolean(
        string="Active",
        default=True,
        index=True,
    )
    last_seen = fields.Datetime(
        string="Last Seen",
        default=fields.Datetime.now,
        help="Last time this session was seen active",
    )

    def _compute_uptime_display(self):
        for rec in self:
            if rec.uptime:
                days, rem = divmod(rec.uptime, 86400)
                hours, rem = divmod(rem, 3600)
                mins, secs = divmod(rem, 60)
                if days:
                    rec.uptime_display = f"{days}d {hours}h {mins}m"
                elif hours:
                    rec.uptime_display = f"{hours}h {mins}m {secs}s"
                else:
                    rec.uptime_display = f"{mins}m {secs}s"
            else:
                rec.uptime_display = "-"

    @api.model
    def sync_sessions(self, device_id, session_type, sessions_data):
        """Sync session table from router data.
        
        Args:
            device_id: ID of the device
            session_type: type of session (pppoe, hotspot, etc.)
            sessions_data: list of dicts with session info from RouterOS
        """
        # Mark all existing sessions of this type as inactive first
        existing = self.search([
            ("device_id", "=", device_id),
            ("session_type", "=", session_type),
            ("is_active", "=", True),
        ])
        existing_by_name = {s.name: s for s in existing}
        
        seen_names = set()
        for sess in sessions_data:
            name = sess.get("name") or sess.get("user")
            if not name:
                continue
            seen_names.add(name)
            
            # Parse uptime string to seconds
            uptime = self._parse_uptime(sess.get("uptime", ""))
            
            vals = {
                "device_id": device_id,
                "session_type": session_type,
                "name": name,
                "address": sess.get("address"),
                "caller_id": sess.get("caller-id"),
                "service": sess.get("service") or sess.get("profile"),
                "interface": sess.get("interface"),
                "uptime": uptime,
                "bytes_in": float(sess.get("bytes-in", 0) or 0),
                "bytes_out": float(sess.get("bytes-out", 0) or 0),
                "is_active": True,
            }
            
            if name in existing_by_name:
                existing_by_name[name].write(vals)
            else:
                self.create(vals)
        
        # Mark sessions not seen as inactive
        for name, sess in existing_by_name.items():
            if name not in seen_names:
                sess.is_active = False

    def _parse_uptime(self, uptime_str):
        """Parse RouterOS uptime string to seconds."""
        if not uptime_str:
            return 0
        
        total = 0
        import re
        
        # Pattern: 1w2d3h4m5s
        weeks = re.search(r"(\d+)w", uptime_str)
        days = re.search(r"(\d+)d", uptime_str)
        hours = re.search(r"(\d+)h", uptime_str)
        mins = re.search(r"(\d+)m", uptime_str)
        secs = re.search(r"(\d+)s", uptime_str)
        
        if weeks:
            total += int(weeks.group(1)) * 604800
        if days:
            total += int(days.group(1)) * 86400
        if hours:
            total += int(hours.group(1)) * 3600
        if mins:
            total += int(mins.group(1)) * 60
        if secs:
            total += int(secs.group(1))
        
        return total
