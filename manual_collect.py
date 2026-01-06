#!/usr/bin/env python3
"""Manually trigger and debug collection"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

dbname = 'qwer'
registry = odoo.registry(dbname)

print("=" * 70)
print("MANUAL COLLECTION DEBUG")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    from odoo.addons.mikrotik_monitoring.collector import async_collector
    
    collector_service = async_collector.get_collector()
    
    if not collector_service:
        print("❌ No collector!")
        sys.exit(1)
    
    print(f"✅ Collector running for: {collector_service.dbname}")
    print(f"   Registered collectors: {len(collector_service._collectors)}")
    
    if len(collector_service._collectors) == 0:
        print("❌ No device collectors registered!")
        sys.exit(1)
    
    # Get first device collector
    device_id, device_collector = list(collector_service._collectors.items())[0]
    
    print(f"\n📱 Device ID: {device_id}")
    print(f"   Host: {device_collector.config['host']}")
    print(f"   Connected: {device_collector.connected}")
    
    # Try to connect if not connected
    if not device_collector.connected:
        print(f"\n🔌 Attempting connection...")
        result = device_collector.connect()
        print(f"   Result: {result}")
        print(f"   Connected now: {device_collector.connected}")
    
    # Try realtime collection
    print(f"\n📊 Attempting realtime collection...")
    try:
        import time
        metrics = device_collector.collect_realtime(time.time())
        
        if metrics:
            print(f"   ✅ Got {len(metrics)} metrics!")
            for key, value in list(metrics.items())[:5]:
                print(f"      - {key}: {value}")
            
            # Store metrics
            print(f"\n💾 Storing metrics...")
            collector_service._store_metrics(env, device_id, metrics)
            cr.commit()
            print(f"   ✅ Metrics stored!")
            
        else:
            print(f"   ⚠️  No metrics returned!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
