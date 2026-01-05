#!/usr/bin/env python3
"""Start collector and verify state updates to UP"""
import odoo
from odoo import api, SUPERUSER_ID
import time

registry = odoo.registry('qwer')

print("Starting collector...")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    print(f"Current state: {device.state}")
    
    result = Device.action_start_collector()
    print(f"✅ {result['params']['message']}")
    cr.commit()

print("\nWaiting 8 seconds for collection...")
time.sleep(8)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    MetricLatest = env['mikrotik.metric.latest']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    print(f"\n📊 Device Status:")
    print(f"  State: {device.state}")
    print(f"  Last Seen: {device.last_seen}")
    
    cpu = MetricLatest.search([
        ('device_id', '=', device.id),
        ('metric_key', '=', 'system.cpu.load_pct')
    ], limit=1)
    
    if cpu:
        print(f"  CPU: {cpu.value_float}%")
        print(f"  Last metric: {cpu.ts_collected}")
    
    if device.state == "up":
        print(f"\n✅ Device state is UP!")
    else:
        print(f"\n⚠️  Device state is {device.state}, expected UP")

print("\n✅ Collector started successfully. Refresh your browser to see updated state.")
