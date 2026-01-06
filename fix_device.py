#!/usr/bin/env python3
"""Fix device state and disable TLS"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    device = Device.search([('name', '=', 'Kendroo')], limit=1)
    
    if device:
        print(f"Current settings:")
        print(f"  State: {device.state}")
        print(f"  Use SSL: {device.use_ssl}")
        print(f"  Collection Enabled: {device.collection_enabled}")
        
        # Update device
        device.write({
            'state': 'up',
            'use_ssl': False,  # Disable TLS to see if that's the issue
        })
        cr.commit()
        
        print(f"\nUpdated settings:")
        print(f"  State: {device.state}")
        print(f"  Use SSL: {device.use_ssl}")
        
        print(f"\n✅ Device updated. Now restarting collector...")
        
cr.commit()
