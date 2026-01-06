#!/usr/bin/env python3
"""Check collector thread status in detail"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

print("=" * 70)
print("COLLECTOR STATUS CHECK - QWER DATABASE")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Import collector
    from odoo.addons.mikrotik_monitoring.collector import async_collector
    
    collector = async_collector.get_collector()
    
    if not collector:
        print("\n❌ Collector object is None!")
        print("   The collector was never started.")
        print("\n   Trying to start collector...")
        async_collector.start_collector(dbname, SUPERUSER_ID)
        collector = async_collector.get_collector()
    
    if collector:
        print(f"\n✅ Collector exists")
        print(f"   Running: {collector.running}")
        print(f"   DB Name: {collector.dbname}")
        print(f"   User ID: {collector.uid}")
        print(f"   Devices tracked: {len(collector._clients)}")
        
        # Check thread
        if hasattr(collector, '_collection_thread'):
            thread = collector._collection_thread
            if thread:
                print(f"\n🧵 Thread Info:")
                print(f"   Alive: {thread.is_alive()}")
                print(f"   Daemon: {thread.daemon}")
                print(f"   Name: {thread.name}")
            else:
                print(f"\n❌ No collection thread exists!")
        
        # Check devices
        Device = env['mikrotik.device']
        devices = Device.search([('collection_enabled', '=', True)])
        
        print(f"\n📡 Devices with collection enabled: {len(devices)}")
        for device in devices:
            print(f"\n   Device: {device.name} (ID: {device.id})")
            print(f"   Host: {device.host}")
            print(f"   State: {device.state}")
            print(f"   Tier: {device.collection_tier}")
            
            # Check if in collector clients
            if device.id in collector._clients:
                print(f"   ✅ Device in collector._clients")
            else:
                print(f"   ❌ Device NOT in collector._clients!")
    else:
        print("\n❌ Collector is still None after start attempt!")
        print("   Check if collector module is loaded correctly.")

print("\n" + "=" * 70)
