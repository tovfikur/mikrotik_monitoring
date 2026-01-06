# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MikrotikDevice(models.Model):
    """MikroTik Router Device - core configuration and status."""

    _name = "mikrotik.device"
    _description = "MikroTik Device"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _rec_name = "name"

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Name",
        required=True,
        index=True,
        help="Friendly name or identity of the router",
    )
    device_uid = fields.Char(
        string="Device UID",
        required=True,
        index=True,
        copy=False,
        help="Unique identifier used by collector (e.g., serial or custom ID)",
    )
    host = fields.Char(
        string="Host / IP",
        required=True,
        help="IP address or DNS hostname of the router",
    )
    api_port = fields.Integer(
        string="API Port",
        default=8728,
        help="RouterOS API port (8728 plain, 8729 TLS)",
    )
    use_ssl = fields.Boolean(
        string="Use TLS",
        default=False,
        help="Connect using TLS (port 8729)",
    )
    username = fields.Char(
        string="Username",
        required=True,
        default="admin",
    )
    password = fields.Char(
        string="Password",
        groups="mikrotik_monitoring.group_mikrotik_admin",
    )
    
    # Status
    state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("up", "Up"),
            ("degraded", "Degraded"),
            ("down", "Down"),
        ],
        string="Status",
        default="unknown",
        readonly=True,
        index=True,
    )
    last_seen = fields.Datetime(
        string="Last Seen",
        readonly=True,
        index=True,
    )
    last_error = fields.Text(
        string="Last Error",
        readonly=True,
    )
    
    # Grouping / Tenancy
    site_id = fields.Many2one(
        "mikrotik.site",
        string="Site",
        index=True,
        ondelete="set null",
    )
    tag_ids = fields.Many2many(
        "mikrotik.tag",
        string="Tags",
    )
    notes = fields.Text(string="Notes")
    
    # Collection settings
    collection_enabled = fields.Boolean(
        string="Collection Enabled",
        default=True,
    )
    ping_target = fields.Char(
        string="Ping Target",
        default="8.8.8.8",
        help="Target IP or hostname to ping for latency monitoring (default: 8.8.8.8 - Google DNS)",
    )
    collection_tier = fields.Selection(
        [
            ("t0", "T0 (1s - Real-time)"),
            ("t1", "T1 (10s - Standard)"),
            ("t2", "T2 (60s - Slow)"),
        ],
        string="Collection Tier",
        default="t1",
        help="Minimum polling interval tier for this device",
    )
    t0_interval = fields.Integer(
        string="T0 Interval (sec)",
        default=1,
        help="High-frequency polling interval",
    )
    t0_max_interfaces = fields.Integer(
        string="T0 Max Interfaces",
        default=10,
        help="Cap on interfaces polled at T0 frequency",
    )
    
    # Advanced collection intervals (in seconds)
    realtime_interval = fields.Integer(
        string="Real-time Interval (sec)",
        default=5,
        help="Interval for system metrics, interface traffic (min: 5)",
    )
    short_interval = fields.Integer(
        string="Short Interval (sec)",
        default=60,
        help="Interval for DHCP, PPP, connections count (min: 30)",
    )
    medium_interval = fields.Integer(
        string="Medium Interval (sec)",
        default=300,
        help="Interval for interfaces inventory, queues (min: 120, default: 5min)",
    )
    long_interval = fields.Integer(
        string="Long Interval (sec)",
        default=3600,
        help="Interval for ARP, routes, firewall rules (min: 600, default: 1hr)",
    )
    extended_interval = fields.Integer(
        string="Extended Interval (sec)",
        default=86400,
        help="Interval for BGP, OSPF, logs, users (min: 3600, default: 24hr)",
    )
    
    # Relations
    capability_id = fields.Many2one(
        "mikrotik.device.capability",
        string="Capabilities",
        readonly=True,
        ondelete="set null",
    )
    interface_ids = fields.One2many(
        "mikrotik.interface",
        "device_id",
        string="Interfaces",
    )
    latest_metric_ids = fields.One2many(
        "mikrotik.metric.latest",
        "device_id",
        string="Latest Metrics",
    )
    event_ids = fields.One2many(
        "mikrotik.event",
        "device_id",
        string="Events",
    )
    lease_ids = fields.One2many(
        "mikrotik.lease",
        "device_id",
        string="DHCP Leases",
    )
    session_ids = fields.One2many(
        "mikrotik.session",
        "device_id",
        string="Sessions",
    )
    
    # Computed
    interface_count = fields.Integer(
        string="Interfaces",
        compute="_compute_interface_count",
        store=True,
    )
    lease_count = fields.Integer(
        string="DHCP Leases",
        compute="_compute_lease_count",
    )
    session_count = fields.Integer(
        string="Sessions",
        compute="_compute_session_count",
    )
    ppp_count = fields.Integer(
        string="PPP Sessions",
        compute="_compute_ppp_count",
    )
    event_count = fields.Integer(
        string="Events",
        compute="_compute_event_count",
    )
    uptime_display = fields.Char(
        string="Uptime",
        compute="_compute_uptime_display",
    )
    
    _sql_constraints = [
        ("device_uid_uniq", "UNIQUE(device_uid)", "Device UID must be unique."),
    ]

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------
    @api.depends("interface_ids")
    def _compute_interface_count(self):
        for rec in self:
            rec.interface_count = len(rec.interface_ids)

    def _compute_lease_count(self):
        for rec in self:
            rec.lease_count = self.env["mikrotik.lease"].search_count([
                ("device_id", "=", rec.id)
            ])

    def _compute_session_count(self):
        for rec in self:
            rec.session_count = self.env["mikrotik.session"].search_count([
                ("device_id", "=", rec.id)
            ])

    def _compute_ppp_count(self):
        for rec in self:
            rec.ppp_count = self.env["mikrotik.session"].search_count([
                ("device_id", "=", rec.id),
                ("session_type", "=", "pppoe"),
                ("is_active", "=", True),
            ])

    def _compute_event_count(self):
        for rec in self:
            rec.event_count = self.env["mikrotik.event"].search_count([
                ("device_id", "=", rec.id)
            ])

    def _compute_uptime_display(self):
        for rec in self:
            uptime_metric = self.env["mikrotik.metric.latest"].search(
                [("device_id", "=", rec.id), ("metric_key", "=", "system.uptime_sec")],
                limit=1,
            )
            if uptime_metric and uptime_metric.value_float:
                secs = int(uptime_metric.value_float)
                days, rem = divmod(secs, 86400)
                hours, rem = divmod(rem, 3600)
                mins, secs = divmod(rem, 60)
                rec.uptime_display = f"{days}d {hours}h {mins}m"
            else:
                rec.uptime_display = "-"

    # -------------------------------------------------------------------------
    # ORM METHODS
    # -------------------------------------------------------------------------
    def write(self, vals):
        """Override write to restart collector when interval settings change."""
        # Check if any interval field is being changed
        interval_fields = {
            'realtime_interval', 'short_interval', 'medium_interval', 
            'long_interval', 'extended_interval', 'collection_enabled'
        }
        
        if interval_fields & set(vals.keys()):
            # Interval settings changed, need to restart collector
            from ..collector.async_collector import get_collector
            
            collector = get_collector()
            if collector and collector.running:
                _logger.info("Interval settings changed, collector will auto-reload")
        
        return super(MikrotikDevice, self).write(vals)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_test_connection(self):
        """Test connectivity to the router and refresh capabilities."""
        self.ensure_one()
        try:
            # Use base.py MikroTikCollector for testing
            from ..collector.base import MikroTikCollector
            
            collector = MikroTikCollector(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.api_port or 8728,
                use_ssl=self.use_ssl,
            )
            
            if not collector.connect():
                raise UserError(_("Failed to connect to device"))
            
            # Get system info to verify connection
            system_info = collector.get_system_info()
            collector.disconnect()
            
            if system_info:
                resource = system_info.get('resource', {})
                identity = system_info.get('identity', {})
                
                # Update capabilities
                capability_data = {
                    "version": resource.get("version", ""),
                    "board-name": resource.get("board-name", ""),
                    "architecture-name": resource.get("architecture-name", ""),
                    "identity": identity.get("name", self.name),
                    "cpu-count": resource.get("cpu-count", "1"),
                    "total-memory": resource.get("total-memory", "0"),
                }
                self._update_capabilities(capability_data)
                
                self.write({
                    "state": "up",
                    "last_seen": fields.Datetime.now(),
                    "last_error": False,
                })
                
                version = resource.get("version", "Unknown")
                device_name = identity.get("name", self.name)
                
                # Reload form to show updated state
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Connection Successful"),
                        "message": _("Connected to %s (RouterOS %s). State updated to UP.") % (device_name, version),
                        "type": "success",
                        "sticky": False,
                        "next": {"type": "ir.actions.act_window_close"},
                    },
                }
            else:
                raise UserError(_("No system information returned"))
                
        except ImportError as e:
            _logger.error(f"Import error in test_connection: {e}")
            self.write({
                "last_error": f"Collector module import error: {str(e)}",
            })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Test Skipped"),
                    "message": _("Collector service not available. Error: %s") % str(e),
                    "type": "warning",
                    "sticky": False,
                },
            }
        except Exception as e:
            _logger.error(f"Connection test failed: {e}")
            self.write({
                "state": "down",
                "last_error": str(e),
            })
            raise UserError(_("Connection failed: %s") % str(e))

    def _update_capabilities(self, data):
        """Update or create capability record from connection test data."""
        self.ensure_one()
        Capability = self.env["mikrotik.device.capability"]
        
        vals = {
            "device_id": self.id,
            "routeros_version": data.get("version", ""),
            "routeros_major": int(data.get("version", "7").split(".")[0]) if data.get("version") else 7,
            "board_name": data.get("board-name", ""),
            "architecture": data.get("architecture-name", ""),
            "identity": data.get("identity", ""),
            "cpu_count": int(data.get("cpu-count", 1)),
            "total_memory": int(data.get("total-memory", 0)),
            "last_refresh": fields.Datetime.now(),
        }
        
        if self.capability_id:
            self.capability_id.write(vals)
        else:
            cap = Capability.create(vals)
            self.capability_id = cap.id

    def action_refresh_capabilities(self):
        """Alias for test connection that focuses on capability refresh."""
        return self.action_test_connection()

    def action_view_live_metrics(self):
        """Open the live metrics view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Live Metrics: %s") % self.name,
            "res_model": "mikrotik.metric.latest",
            "view_mode": "tree",
            "domain": [("device_id", "=", self.id)],
            "context": {"default_device_id": self.id},
        }

    # -------------------------------------------------------------------------
    # ASYNC COLLECTOR CONTROL
    # -------------------------------------------------------------------------
    def action_start_collector(self):
        """Start the async collector service."""
        from ..collector.async_collector import start_collector, get_collector
        
        collector = get_collector()
        if collector and collector.running:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Collector"),
                    "message": _("Collector is already running."),
                    "type": "warning",
                    "sticky": False,
                },
            }
        
        start_collector(self.env.cr.dbname, self.env.uid)
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Collector Started"),
                "message": _("Background collector service started. Collecting every 5 seconds."),
                "type": "success",
                "sticky": False,
            },
        }
    
    def action_stop_collector(self):
        """Stop the async collector service."""
        from ..collector.async_collector import stop_collector, get_collector
        
        collector = get_collector()
        if not collector or not collector.running:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Collector"),
                    "message": _("Collector is not running."),
                    "type": "warning",
                    "sticky": False,
                },
            }
        
        stop_collector()
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Collector Stopped"),
                "message": _("Background collector service stopped."),
                "type": "info",
                "sticky": False,
            },
        }
    
    def get_collector_status(self):
        """Get the current collector status."""
        from ..collector.async_collector import get_collector
        
        collector = get_collector()
        if collector and collector.running:
            return {
                "running": True,
                "device_count": len(collector._clients),
            }
        return {"running": False, "device_count": 0}
    
    def action_refresh_collector_client(self):
        """Refresh the collector's client for this device (after credential change)."""
        self.ensure_one()
        from ..collector.async_collector import get_collector
        
        collector = get_collector()
        if collector and collector.running:
            collector.refresh_client(self.id)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Client Refreshed"),
                    "message": _("Collector will reconnect to %s on next cycle.") % self.name,
                    "type": "success",
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Collector Not Running"),
                "message": _("Start the collector first."),
                "type": "warning",
                "sticky": False,
            },
        }

    # -------------------------------------------------------------------------
    # BUSINESS LOGIC
    # -------------------------------------------------------------------------
    def update_state_from_metrics(self):
        """Update device state based on freshness of metrics."""
        now = fields.Datetime.now()
        stale_threshold = now - timedelta(seconds=30)
        down_threshold = now - timedelta(seconds=120)
        
        for device in self:
            if not device.last_seen:
                device.state = "unknown"
            elif device.last_seen < down_threshold:
                device.state = "down"
            elif device.last_seen < stale_threshold:
                device.state = "degraded"
            else:
                device.state = "up"

    @api.model
    def get_active_devices_for_collection(self):
        """Return devices that should be polled by the collector."""
        return self.search([
            ("collection_enabled", "=", True),
        ])

    @api.model
    def get_device_config_for_collector(self):
        """Return device configuration as dict for collector service."""
        devices = self.get_active_devices_for_collection()
        result = []
        
        for d in devices:
            # Get T0-enabled interfaces
            t0_interfaces = d.interface_ids.filtered(lambda i: i.t0_enabled).mapped("name")
            
            result.append({
                "device_uid": d.device_uid,
                "host": d.host,
                "port": d.api_port,
                "username": d.username,
                "password": d.password,
                "use_ssl": d.use_ssl,
                "ping_target": d.ping_target or "8.8.8.8",
                "collection_tier": d.collection_tier,
                "t0_interval": d.t0_interval,
                "t0_max_interfaces": d.t0_max_interfaces,
                "t0_interfaces": t0_interfaces[:d.t0_max_interfaces],  # Apply cap
            })
        
        return result

    @api.model
    def _check_device_health(self):
        """Cron job to check device health and update states."""
        now = fields.Datetime.now()
        stale_threshold = now - timedelta(seconds=30)
        down_threshold = now - timedelta(seconds=120)
        
        # Find stale devices
        stale_devices = self.search([
            ("collection_enabled", "=", True),
            ("state", "=", "up"),
            ("last_seen", "<", stale_threshold),
            ("last_seen", ">=", down_threshold),
        ])
        
        if stale_devices:
            stale_devices.write({"state": "degraded"})
            for device in stale_devices:
                self.env["mikrotik.event"].log_event(
                    device_id=device.id,
                    event_type="device_degraded",
                    subject=device.device_uid,
                    message=f"Device not responding for >30s",
                    severity="warning",
                )
        
        # Find down devices
        down_devices = self.search([
            ("collection_enabled", "=", True),
            ("state", "in", ["up", "degraded"]),
            ("last_seen", "<", down_threshold),
        ])
        
        if down_devices:
            down_devices.write({"state": "down"})
            for device in down_devices:
                self.env["mikrotik.event"].log_event(
                    device_id=device.id,
                    event_type="device_down",
                    subject=device.device_uid,
                    message=f"Device not responding for >120s",
                    severity="error",
                )

    def action_view_interfaces(self):
        """Open interfaces view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Interfaces: %s") % self.name,
            "res_model": "mikrotik.interface",
            "view_mode": "tree,form",
            "domain": [("device_id", "=", self.id)],
            "context": {"default_device_id": self.id},
        }

    def action_view_leases(self):
        """Open DHCP leases view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("DHCP Leases: %s") % self.name,
            "res_model": "mikrotik.lease",
            "view_mode": "tree,form",
            "domain": [("device_id", "=", self.id)],
            "context": {"default_device_id": self.id},
        }

    def action_view_sessions(self):
        """Open sessions view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sessions: %s") % self.name,
            "res_model": "mikrotik.session",
            "view_mode": "tree,form",
            "domain": [("device_id", "=", self.id)],
            "context": {"default_device_id": self.id},
        }

    def action_view_ppp(self):
        """Open PPP sessions view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("PPP Sessions: %s") % self.name,
            "res_model": "mikrotik.session",
            "view_mode": "tree,form",
            "domain": [
                ("device_id", "=", self.id),
                ("session_type", "=", "pppoe"),
            ],
            "context": {
                "default_device_id": self.id,
                "default_session_type": "pppoe",
            },
        }

    def action_view_events(self):
        """Open events view for this device."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Events: %s") % self.name,
            "res_model": "mikrotik.event",
            "view_mode": "tree,form",
            "domain": [("device_id", "=", self.id)],
            "context": {"default_device_id": self.id},
        }

    @api.model
    def _ensure_collector_running(self):
        """Watchdog to ensure the async collector is running.
        Called by cron every 5 minutes."""
        from ..collector import async_collector
        
        collector = async_collector.get_collector()
        if collector is None or not collector.running:
            _logger.warning("🔄 Collector not running, attempting to restart...")
            dbname = self.env.cr.dbname
            try:
                async_collector.start_collector(dbname, self.env.uid)
                _logger.info("✅ Collector restarted successfully")
            except Exception as e:
                _logger.error(f"❌ Failed to restart collector: {e}")
        else:
            # Check if configuration changed
            enabled_count = self.search_count([('collection_enabled', '=', True)])
            if enabled_count > 0:
                _logger.debug(f"✅ Collector running, monitoring {enabled_count} devices")


class MikrotikSite(models.Model):
    """Site/Location grouping for devices."""

    _name = "mikrotik.site"
    _description = "MikroTik Site"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", index=True)
    location = fields.Char(string="Location", help="Physical location or address")
    description = fields.Text(string="Description")
    device_ids = fields.One2many("mikrotik.device", "site_id", string="Devices")
    device_count = fields.Integer(
        string="Devices",
        compute="_compute_device_count",
        store=True,
    )

    @api.depends("device_ids")
    def _compute_device_count(self):
        for rec in self:
            rec.device_count = len(rec.device_ids)


class MikrotikTag(models.Model):
    """Tags for device classification (e.g., SLA, uplink, critical)."""

    _name = "mikrotik.tag"
    _description = "MikroTik Tag"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    color = fields.Integer(string="Color Index", default=0)
    is_sla = fields.Boolean(
        string="SLA Tag",
        help="Interfaces with this tag are always included in T0 collection",
    )
