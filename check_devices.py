#!/usr/bin/env python3
"""Check device collection status"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'odoo'
registry = odoo.registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    all_devices = Device.search([])
    print(f"Total devices: {len(all_devices)}")
    
    for device in all_devices:
        print(f"\nDevice: {device.name} (ID: {device.id})")
        print(f"  Collection Enabled: {device.collection_enabled}")
        print(f"  State: {device.state}")
        print(f"  Host: {device.host}")
        print(f"  Last Seen: {device.last_seen}")
    
    enabled = Device.search([('collection_enabled', '=', True)])
    print(f"\n✅ Devices with collection enabled: {len(enabled)}")
    for d in enabled:
        print(f"   - {d.name}")
