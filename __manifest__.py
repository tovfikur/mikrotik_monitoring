# -*- coding: utf-8 -*-

{
    "name": "MikroTik Monitoring",
    "version": "17.0.1.0.0",
    "category": "Operations/Network",
    "summary": "ISP-grade real-time monitoring for MikroTik RouterOS devices",
    "description": """
MikroTik RouterOS Monitoring for Odoo 17
========================================

Professional ISP-grade monitoring solution for MikroTik routers:

Features
--------
* Real-time telemetry with 1-second resolution
* Tiered collection (T0=1s, T1=10s, T2=60s, T3=15min)
* Interface traffic monitoring with dynamic T0 selection
* DHCP lease tracking for 20k+ end users
* PPPoE/Hotspot session monitoring
* RouterOS v6 and v7 compatible
* Event logging and alerting
* 90-day data retention with automatic cleanup

Architecture
------------
* Append-only time-series storage (mikrotik.metric.point)
* Latest snapshot table for fast UI reads (mikrotik.metric.latest)
* Bus-based live updates for real-time dashboards
* External collector service for high-frequency polling

Scale
-----
* Designed for 3+ routers with 30+ interfaces each
* Supports 20,000+ concurrent DHCP/PPP users
* Optimized bulk inserts for high-throughput ingestion
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "bus", "mail"],
    "data": [
        # Security
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        # Views
        "views/mikrotik_device_views.xml",
        "views/mikrotik_interface_views.xml",
        "views/mikrotik_metric_views.xml",
        "views/mikrotik_event_views.xml",
        "views/mikrotik_lease_views.xml",
        "views/mikrotik_session_views.xml",
        "views/mikrotik_site_views.xml",
        "views/menu.xml",
        # Data
        "data/cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mikrotik_monitoring/static/src/css/mikrotik_monitoring.css",
            "mikrotik_monitoring/static/src/js/mikrotik_live.js",
            "mikrotik_monitoring/static/src/xml/mikrotik_live.xml",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
    "external_dependencies": {
        "python": ["routeros_api"],
    },
}
