# MikroTik Monitoring Module for Odoo 17

ISP-grade real-time monitoring solution for MikroTik RouterOS devices.

## Quick Install

1. Copy this module to your Odoo addons path
2. Update Odoo module list
3. Install "MikroTik Monitoring"

## Documentation

See `static/description/index.html` for full documentation.

## Architecture

```
mikrotik_monitoring/
├── __manifest__.py          # Module manifest
├── __init__.py              # Python imports
├── controllers/             # HTTP API endpoints
│   ├── ingest.py           # Collector ingestion API
│   └── api.py              # Device config API
├── models/                  # Odoo models
│   ├── mikrotik_device.py  # Device, Site, Tag
│   ├── mikrotik_capability.py
│   ├── mikrotik_metric_catalog.py
│   ├── mikrotik_metric_point.py  # Time-series storage
│   ├── mikrotik_metric_latest.py # Latest snapshot
│   ├── mikrotik_event.py
│   ├── mikrotik_interface.py
│   ├── mikrotik_lease.py
│   └── mikrotik_session.py
├── views/                   # UI views
├── security/                # Access control
├── data/                    # Cron jobs
├── static/                  # JS, CSS, icons
│   └── src/
│       ├── js/mikrotik_live.js
│       ├── css/mikrotik_monitoring.css
│       └── xml/mikrotik_live.xml
└── collector/               # External collector service
    ├── collector.py
    ├── requirements.txt
    └── config.example.yaml
```

## Collector Service

The collector is a separate Python process that polls MikroTik devices
and pushes data to Odoo via HTTP. See `collector/README.md` for setup.

## License

LGPL-3

# mikrotik_monitoring

This repository contains the Mikrotik Monitoring module for Odoo. It provides tools for monitoring Mikrotik devices, including device state, DHCP leases, and PPP session management.
