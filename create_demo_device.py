#!/usr/bin/env python3
"""
Quick Setup: Create Sample Device
Creates a test device so you can see the graphs
"""

import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'odoo'
registry = odoo.registry(dbname)

print("=" * 70)
print("CREATING SAMPLE MIKROTIK DEVICE")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    
    # Check if device already exists
    existing = Device.search([('name', '=', 'Demo Router')])
    if existing:
        print(f"\n✅ Device already exists: {existing.name} (ID: {existing.id})")
        device = existing
    else:
        # Create sample device
        import uuid
        device = Device.create({
            'name': 'Demo Router',
            'device_uid': str(uuid.uuid4()),
            'host': '192.168.88.1',
            'api_port': 8728,
            'username': 'admin',
            'password': 'demo',
            'collection_enabled': False,  # Don't actually try to connect
        })
        print(f"\n✅ Created demo device: {device.name} (ID: {device.id})")
    
    cr.commit()
    
    print("\n" + "=" * 70)
    print("DEVICE CREATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nDevice ID: {device.id}")
    print(f"Name: {device.name}")
    print("\n💡 Next step: Run generate_test_data.py to create sample metrics")
    print("=" * 70)
