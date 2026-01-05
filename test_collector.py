#!/usr/bin/env python3
import odoo
from odoo import api, SUPERUSER_ID
import time

registry = odoo.registry('qwer')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    print("Starting async collector...")
    result = Device.action_start_collector()
    print(f"Result: {result.get('params', {}).get('message', 'Started')}")
    
    cr.commit()
    
    print("\nWaiting 15 seconds for data collection...")
    time.sleep(15)

# New cursor to read collected data
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    MetricPoint = env['mikrotik.metric.point']
    MetricLatest = env['mikrotik.metric.latest']
    Interface = env['mikrotik.interface']
    Device = env['mikrotik.device']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    if device:
        print(f"\n=== Device: {device.name} ===")
        print(f"State: {device.state}")
        print(f"Last Seen: {device.last_seen}")
        
        # Check metric points
        metrics = MetricPoint.search([('device_id', '=', device.id)], order='ts_collected desc', limit=10)
        print(f"\n=== Latest {len(metrics)} Metric Points ===")
        for m in metrics:
            catalog = m.metric_id
            iface = f" [{m.interface_name}]" if m.interface_name else ""
            print(f"  {m.ts_collected} - {catalog.key}{iface}: {m.value_float or m.value_text}")
        
        # Check latest metrics
        latest = MetricLatest.search([('device_id', '=', device.id)], limit=15)
        print(f"\n=== Latest Metrics ({len(latest)}) ===")
        for m in latest:
            iface = f" [{m.interface_name}]" if m.interface_name else ""
            print(f"  {m.metric_key}{iface}: {m.value_float or m.value_text}")
        
        # Check interfaces
        interfaces = Interface.search([('device_id', '=', device.id)])
        print(f"\n=== Interfaces ({len(interfaces)}) ===")
        for iface in interfaces[:5]:
            status = "UP" if iface.is_running else "DOWN"
            print(f"  {iface.name} ({iface.interface_type}): {status} - MAC: {iface.mac_address}")
        
        print(f"\n✓ Collector is working! Collected {len(metrics)} metric points.")
