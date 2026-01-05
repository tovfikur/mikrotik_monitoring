#!/usr/bin/env python3
import odoo
from odoo import api, SUPERUSER_ID

registry = odoo.registry('qwer')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    # Find device
    devices = Device.search([('host', '=', '192.168.50.1')])
    
    if devices:
        for d in devices:
            print(f"Found device: {d.name}")
            print(f"  ID: {d.id}")
            print(f"  Host: {d.host}:{d.api_port}")
            print(f"  Username: {d.username}")
            print(f"  Collection Enabled: {d.collection_enabled}")
            print(f"  Realtime Interval: {d.realtime_interval}s")
            print(f"  Short Interval: {d.short_interval}s")
            print(f"  Medium Interval: {d.medium_interval}s")
            print(f"  Long Interval: {d.long_interval}s")
            print(f"  Extended Interval: {d.extended_interval}s")
            
            # Update password to 'billing'
            print("\nUpdating credentials to billing/billing...")
            d.write({
                'username': 'billing',
                'password': 'billing',
                'collection_enabled': True,
            })
            print("Done!")
    else:
        print("No device found at 192.168.50.1")
        print("Creating device...")
        device = Device.create({
            'name': 'kendroo',
            'device_uid': 'kendroo-main',
            'host': '192.168.50.1',
            'api_port': 8728,
            'username': 'billing',
            'password': 'billing',
            'collection_enabled': True,
            'realtime_interval': 5,
            'short_interval': 60,
            'medium_interval': 300,
            'long_interval': 3600,
            'extended_interval': 86400,
        })
        print(f"Created device: {device.name} (ID: {device.id})")
    
    cr.commit()
