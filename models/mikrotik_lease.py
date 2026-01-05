# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MikrotikLease(models.Model):
    """DHCP Lease current state table.
    
    For 20k+ end-users, this stores current state (upserted),
    not time-series. Use mikrotik.event for lease events.
    """

    _name = "mikrotik.lease"
    _description = "MikroTik DHCP Lease"
    _order = "device_id, address"

    device_id = fields.Many2one(
        "mikrotik.device",
        string="Device",
        required=True,
        index=True,
        ondelete="cascade",
    )
    
    address = fields.Char(
        string="IP Address",
        required=True,
        index=True,
    )
    mac_address = fields.Char(
        string="MAC Address",
        index=True,
    )
    client_id = fields.Char(
        string="Client ID",
    )
    hostname = fields.Char(
        string="Hostname",
    )
    
    server = fields.Char(
        string="DHCP Server",
    )
    
    status = fields.Selection(
        [
            ("bound", "Bound"),
            ("waiting", "Waiting"),
            ("offered", "Offered"),
            ("expired", "Expired"),
        ],
        string="Status",
        default="bound",
    )
    
    expires_at = fields.Datetime(
        string="Expires At",
    )
    last_seen = fields.Datetime(
        string="Last Seen",
        default=fields.Datetime.now,
    )
    
    # For static bindings
    is_static = fields.Boolean(
        string="Static Binding",
        default=False,
    )

    _sql_constraints = [
        (
            "device_address_uniq",
            "UNIQUE(device_id, address)",
            "IP address must be unique per device.",
        ),
    ]

    @api.model
    def sync_leases(self, device_id, leases_data):
        """Sync lease table from router data.
        
        Args:
            device_id: ID of the device
            leases_data: list of dicts with lease info from RouterOS
        """
        # Get existing leases
        existing = {l.address: l for l in self.search([("device_id", "=", device_id)])}
        
        seen_addresses = set()
        for lease in leases_data:
            addr = lease.get("address")
            if not addr:
                continue
            seen_addresses.add(addr)
            
            vals = {
                "device_id": device_id,
                "address": addr,
                "mac_address": lease.get("mac-address"),
                "client_id": lease.get("client-id"),
                "hostname": lease.get("host-name"),
                "server": lease.get("server"),
                "status": self._map_status(lease.get("status", "bound")),
                "last_seen": fields.Datetime.now(),
                "is_static": lease.get("dynamic") == "false",
            }
            
            if addr in existing:
                existing[addr].write(vals)
            else:
                self.create(vals)
        
        # Mark expired leases
        for addr, lease in existing.items():
            if addr not in seen_addresses:
                lease.status = "expired"

    def _map_status(self, ros_status):
        """Map RouterOS status to our selection."""
        status_map = {
            "bound": "bound",
            "waiting": "waiting",
            "offered": "offered",
        }
        return status_map.get(ros_status, "bound")
