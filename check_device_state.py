#!/usr/bin/env python3
"""Check device state and collector status"""
import odoo
from odoo import api, SUPERUSER_ID

registry = odoo.registry('qwer')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    MetricLatest = env['mikrotik.metric.latest']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    print(f"Device: {device.name}")
    print(f"State: {device.state}")
    print(f"Collection Enabled: {device.collection_enabled}")
    print(f"Last Seen: {device.last_seen}")
    print(f"Last Error: {device.last_error or 'None'}")
    
    # Check if collector is running
    from odoo.addons.mikrotik_monitoring.collector.async_collector import get_collector
    
    collector = get_collector()
    if collector:
        print(f"\n✅ Collector Running: {collector.running}")
        print(f"Active Devices: {len(collector._collectors)}")
        
        if device.id in collector._collectors:
            dc = collector._collectors[device.id]
            print(f"\n📡 Device Collector:")
            print(f"  Connected: {dc.connected}")
            print(f"  Realtime interval: {dc.realtime_interval}s")
            print(f"  Last realtime: {dc._last_realtime}")
        else:
            print(f"\n⚠️  Device not in active collectors!")
    else:
        print(f"\n❌ Collector not running")
    
    # Check recent metrics
    recent = MetricLatest.search([
        ('device_id', '=', device.id),
        ('metric_key', '=', 'system.cpu.load_pct')
    ], limit=1)
    
    if recent:
        print(f"\n📊 Recent Metrics:")
        print(f"  CPU: {recent.value_float}%")
        print(f"  Last Update: {recent.ts_collected}")
    else:
        print(f"\n⚠️  No recent metrics found")
