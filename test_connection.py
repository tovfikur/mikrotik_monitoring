#!/usr/bin/env python3
"""Test the action_test_connection button"""
import odoo
from odoo import api, SUPERUSER_ID

registry = odoo.registry('qwer')

print("Testing action_test_connection...")

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    if not device:
        print("❌ Device not found")
        exit(1)
    
    print(f"Device: {device.name}")
    print(f"Testing connection to {device.host}:{device.api_port}")
    
    result = device.action_test_connection()
    
    print(f"\n✅ Result:")
    print(f"  Type: {result.get('type')}")
    print(f"  Notification: {result.get('params', {}).get('title')}")
    print(f"  Message: {result.get('params', {}).get('message')}")
    print(f"  Status: {result.get('params', {}).get('type')}")
    
    # Refresh device
    device.invalidate_recordset()
    print(f"\n📊 Device State:")
    print(f"  State: {device.state}")
    print(f"  Last Seen: {device.last_seen}")
    print(f"  Last Error: {device.last_error or 'None'}")
    
    if device.capability_id:
        cap = device.capability_id
        print(f"\n🔧 Capabilities:")
        print(f"  RouterOS: {cap.routeros_version}")
        print(f"  Board: {cap.board_name}")
        print(f"  Identity: {cap.identity}")
        print(f"  CPUs: {cap.cpu_count}")
        print(f"  Memory: {cap.total_memory / (1024*1024):.0f} MB")
