#!/usr/bin/env python3
"""Monitor real-time collection on qwer database"""
import sys
import time
from datetime import datetime, timedelta
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'  # Use correct database
registry = odoo.registry(dbname)

print("=" * 70)
print("REAL-TIME COLLECTION MONITOR - QWER DATABASE")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    MetricPoint = env['mikrotik.metric.point']
    
    devices = Device.search([('collection_enabled', '=', True)])
    
    if not devices:
        print("\n❌ No devices with collection enabled!")
        sys.exit(1)
    
    print(f"\n📡 Monitoring {len(devices)} device(s):")
    for device in devices:
        print(f"   - {device.name} ({device.host}) - State: {device.state}")
        print(f"     Last seen: {device.last_seen or 'Never'}")
    
    # Get initial count
    initial_count = MetricPoint.search_count([
        ('device_id', 'in', devices.ids),
        ('ts_collected', '>=', (datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S'))
    ])
    
    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Metrics in last 2 min: {initial_count}")
    
    # Get latest metric
    latest = MetricPoint.search([
        ('device_id', 'in', devices.ids)
    ], limit=1, order='ts_collected desc')
    
    if latest:
        age = (datetime.now() - latest.ts_collected).total_seconds()
        print(f"   Latest: {latest.metric_id.key} = {latest.value_float:.2f} ({age:.0f}s ago)")
        
        if age > 60:
            print(f"\n   ⚠️  WARNING: Latest metric is {age:.0f} seconds old!")
            print(f"   Collector may have stopped or device is unreachable.")
    
    print("\n" + "=" * 70)
    print("WATCHING FOR NEW METRICS (30 seconds)...")
    print("=" * 70)
    
    try:
        for i in range(6):
            time.sleep(5)
            cr.commit()
            
            current_count = MetricPoint.search_count([
                ('device_id', 'in', devices.ids),
                ('ts_collected', '>=', (datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S'))
            ])
            
            new_metrics = current_count - initial_count
            
            latest = MetricPoint.search([
                ('device_id', 'in', devices.ids)
            ], limit=3, order='ts_collected desc')
            
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Total: {current_count} (+{new_metrics} new)")
            
            if latest:
                for point in latest:
                    age = (datetime.now() - point.ts_collected).total_seconds()
                    print(f"   • {point.metric_id.key} = {point.value_float:.2f} ({age:.0f}s ago)")
            
            initial_count = current_count
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped")
    
    print("\n" + "=" * 70)
    print("If you see '+0 new' and old timestamps, the collector needs restart.")
    print("Click 'Start Collector' button on the device form to restart it.")
    print("=" * 70)
