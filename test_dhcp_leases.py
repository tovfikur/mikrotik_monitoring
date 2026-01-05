#!/usr/bin/env python3
"""Test DHCP lease collection"""
import odoo
from odoo import api, SUPERUSER_ID
import time

registry = odoo.registry('qwer')

print("Starting collector and testing DHCP lease collection...")

# Start collector
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    print(f"Device: {device.name}")
    
    # Check current lease count
    Lease = env['mikrotik.lease']
    current_leases = Lease.search([('device_id', '=', device.id)])
    print(f"Current leases in DB: {len(current_leases)}")
    
    result = Device.action_start_collector()
    print(f"\n✅ {result['params']['message']}")
    cr.commit()

print("\nWaiting 70 seconds for short interval collection (includes DHCP leases)...")
time.sleep(70)

# Check collected leases
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    Lease = env['mikrotik.lease']
    MetricLatest = env['mikrotik.metric.latest']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    # Get DHCP leases
    leases = Lease.search([('device_id', '=', device.id)])
    
    print(f"\n📊 DHCP Leases Collected:")
    print(f"  Total leases: {len(leases)}")
    
    if leases:
        print(f"\n  Sample leases (first 10):")
        for lease in leases[:10]:
            status = "✓" if lease.status == "bound" else "○"
            hostname = lease.hostname or "(no hostname)"
            print(f"    {status} {lease.address:15s} {lease.mac_address:17s} {hostname}")
        
        # Check metrics
        dhcp_metric = MetricLatest.search([
            ('device_id', '=', device.id),
            ('metric_key', '=', 'dhcp.active_leases')
        ], limit=1)
        
        if dhcp_metric:
            print(f"\n  Active leases (metric): {int(dhcp_metric.value_float)}")
        
        print(f"\n✅ DHCP leases are being collected!")
    else:
        print(f"\n❌ No leases collected yet. Check logs for errors.")
        print(f"   Router should have leases at 192.168.50.1")

print("\n✅ Test complete. Check Odoo UI: MikroTik → Devices → Kendroo → DHCP Leases tab")
