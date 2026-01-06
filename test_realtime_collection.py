#!/usr/bin/env python3
"""
Test Real-Time Collection
Monitors metric collection in real-time to verify 5-second collection
"""

import sys
import time
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID
from datetime import datetime, timedelta

# Connect to database
dbname = 'odoo'
registry = odoo.registry(dbname)

print("=" * 70)
print("REAL-TIME COLLECTION MONITOR")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    MetricPoint = env['mikrotik.metric.point']
    
    # Get devices with collection enabled
    devices = Device.search([('collection_enabled', '=', True)])
    
    if not devices:
        print("\n❌ No devices with collection enabled!")
        print("\n💡 To enable collection:")
        print("   1. Go to: MikroTik Monitoring > Devices")
        print("   2. Open a device")
        print("   3. Enable 'Collection Enabled' in Live Dashboard tab")
        print("   4. Configure connection credentials (host, username, password)")
        print("   5. Test connection first (Test Connection button)")
        sys.exit(1)
    
    print(f"\n📡 Monitoring {len(devices)} device(s) with collection enabled:")
    for device in devices:
        print(f"   - {device.name} ({device.host})")
        print(f"     Status: {device.state}")
        print(f"     Last seen: {device.last_seen or 'Never'}")
    
    print("\n" + "=" * 70)
    print("WATCHING FOR NEW METRICS (30 seconds)...")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    
    # Get initial count
    initial_count = MetricPoint.search_count([
        ('device_id', 'in', devices.ids),
        ('ts_collected', '>=', (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'))
    ])
    
    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Initial metric count (last 1 min): {initial_count}")
    
    try:
        for i in range(6):  # Monitor for 30 seconds (6 x 5-second intervals)
            time.sleep(5)
            cr.commit()  # Refresh to see new data
            
            current_count = MetricPoint.search_count([
                ('device_id', 'in', devices.ids),
                ('ts_collected', '>=', (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'))
            ])
            
            new_metrics = current_count - initial_count
            
            # Get latest metrics
            latest = MetricPoint.search([
                ('device_id', 'in', devices.ids)
            ], limit=5, order='ts_collected desc')
            
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Total metrics: {current_count} (+{new_metrics} new)")
            
            if latest:
                print(f"   Latest metrics:")
                for point in latest:
                    age_seconds = (datetime.now() - point.ts_collected).total_seconds()
                    print(f"   • {point.device_id.name}: {point.metric_id.key} = {point.value_float:.2f} ({age_seconds:.0f}s ago)")
            else:
                print(f"   ⚠️  No metrics found yet - collector may still be connecting")
            
            initial_count = current_count
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    
    print("\n" + "=" * 70)
    print("COLLECTION SUMMARY")
    print("=" * 70)
    
    # Final statistics
    for device in devices:
        total = MetricPoint.search_count([('device_id', '=', device.id)])
        last_minute = MetricPoint.search_count([
            ('device_id', '=', device.id),
            ('ts_collected', '>=', (datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'))
        ])
        
        print(f"\n📊 {device.name}:")
        print(f"   Total metrics: {total}")
        print(f"   Last minute: {last_minute}")
        print(f"   Rate: ~{last_minute / 60:.1f} metrics/second")
        
        if last_minute > 0:
            print(f"   ✅ Collection is working!")
        else:
            print(f"   ⚠️  No recent metrics - check device connection")

print("\n" + "=" * 70)
print("💡 TIP: Graphs will update automatically as metrics are collected")
print("   View graphs: Device Form > 'Monitoring Graphs' button")
print("=" * 70)
