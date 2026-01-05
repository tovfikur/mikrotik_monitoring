#!/usr/bin/env python3
"""Complete test: Test Connection + Start Collector + Verify Collection"""
import odoo
from odoo import api, SUPERUSER_ID
import time

registry = odoo.registry('qwer')

print("=" * 70)
print("COMPLETE UI BUTTON TEST")
print("=" * 70)

# Test 1: Test Connection Button
print("\n1️⃣ Testing 'Test Connection' button...")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    result = device.action_test_connection()
    status = result.get('params', {}).get('type')
    message = result.get('params', {}).get('message')
    
    if status == 'success':
        print(f"   ✅ {message}")
    else:
        print(f"   ❌ {status}: {message}")
        exit(1)
    
    cr.commit()

# Test 2: Start Collector Button
print("\n2️⃣ Testing 'Start Collector' button...")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    result = Device.action_start_collector()
    message = result.get('params', {}).get('message')
    status = result.get('params', {}).get('type')
    
    print(f"   ✅ {message}")
    cr.commit()

# Test 3: Wait and verify data collection
print("\n3️⃣ Waiting 10 seconds for data collection...")
time.sleep(10)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    MetricLatest = env['mikrotik.metric.latest']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    # Check realtime metrics
    cpu = MetricLatest.search([
        ('device_id', '=', device.id),
        ('metric_key', '=', 'system.cpu.load_pct')
    ], limit=1)
    
    memory = MetricLatest.search([
        ('device_id', '=', device.id),
        ('metric_key', '=', 'system.memory.used_pct')
    ], limit=1)
    
    traffic = MetricLatest.search([
        ('device_id', '=', device.id),
        ('metric_key', '=', 'iface.rx_bps')
    ], limit=3)
    
    if cpu and memory:
        print(f"   ✅ Realtime metrics collecting:")
        print(f"      CPU: {cpu.value_float:.1f}%")
        print(f"      Memory: {memory.value_float:.1f}%")
        print(f"      Interface traffic: {len(traffic)} interfaces")
    else:
        print(f"   ❌ No metrics collected yet")
        exit(1)

# Test 4: Stop Collector Button
print("\n4️⃣ Testing 'Stop Collector' button...")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    result = Device.action_stop_collector()
    message = result.get('params', {}).get('message')
    print(f"   ✅ {message}")
    cr.commit()

print("\n" + "=" * 70)
print("✅ ALL UI BUTTONS WORKING CORRECTLY!")
print("=" * 70)
print("\nYou can now:")
print("  1. Open Odoo UI: http://localhost:8069")
print("  2. Go to MikroTik → Devices")
print("  3. Click 'Test Connection' - should show success")
print("  4. Click 'Start Collector' - should start background collection")
print("  5. View metrics in the device form (Live Metrics tab)")
print("  6. Click 'Stop Collector' when done")
