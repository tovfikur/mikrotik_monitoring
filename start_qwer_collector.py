#!/usr/bin/env python3
"""Start collector for qwer database"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

print("=" * 70)
print("STARTING COLLECTOR FOR QWER DATABASE")
print("=" * 70)

# Load qwer registry first to ensure module is loaded
registry = odoo.registry('qwer')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Now import collector (module should be loaded)
    from odoo.addons.mikrotik_monitoring.collector import async_collector
    
    # Stop existing collector
    print("\n🛑 Stopping existing collector...")
    async_collector.stop_collector()
    
    # Start for qwer database
    print("🚀 Starting collector for 'qwer' database...")
    collector = async_collector.start_collector('qwer', SUPERUSER_ID)
    
    print(f"\n✅ Collector started!")
    print(f"   DB: {collector.dbname}")
    print(f"   Running: {collector.running}")
    
    # Force reload to register devices
    print(f"\n🔄 Forcing reload to register devices...")
    collector._reload_collectors(env)
    
    with collector._lock:
        print(f"   Collectors registered: {len(collector._collectors)}")
        for device_id in collector._collectors.keys():
            print(f"   - Device ID: {device_id}")
    
    cr.commit()

print("\n" + "=" * 70)
print("Now wait 10 seconds and check for new metrics!")
print("=" * 70)
