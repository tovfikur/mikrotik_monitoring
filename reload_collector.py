#!/usr/bin/env python3
"""Force reload collector configuration"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

print("=" * 70)
print("RELOADING COLLECTOR CONFIGURATION")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    device = Device.search([('name', '=', 'Kendroo')], limit=1)
    
    if device:
        print(f"\n📱 Device: {device.name}")
        print(f"   Current state: {device.state}")
        print(f"   Collection enabled: {device.collection_enabled}")
        
        # Force state to up
        print(f"\n🔄 Resetting device state to 'up'...")
        device.write({'state': 'up'})
        cr.commit()
        
        print(f"   New state: {device.state}")
        
        # Reload collector
        print(f"\n🔄 Reloading collector...")
        from odoo.addons.mikrotik_monitoring.collector import async_collector
        
        collector = async_collector.get_collector()
        if collector:
            print(f"   Calling reload_configuration()...")
            collector.reload_configuration()
            print(f"   ✅ Collector reloaded!")
        else:
            print(f"   ❌ Collector not found!")
    
    cr.commit()

print("\n" + "=" * 70)
print("Wait 10 seconds then check for new metrics")
print("=" * 70)
