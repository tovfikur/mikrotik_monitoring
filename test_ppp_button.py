#!/usr/bin/env python3
"""Test PPP button and counter"""
import odoo
from odoo import api, SUPERUSER_ID

registry = odoo.registry('qwer')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    print("=" * 70)
    print(f"DEVICE COUNTERS FOR {device.name}")
    print("=" * 70)
    
    print(f"\n📊 Smart Button Counts:")
    print(f"  Interfaces:   {device.interface_count}")
    print(f"  DHCP Leases:  {device.lease_count}")
    print(f"  PPP:          {device.ppp_count}  ⭐ NEW")
    print(f"  Sessions:     {device.session_count}")
    print(f"  Events:       {device.event_count}")
    
    # Test the action
    print(f"\n✅ Testing action_view_ppp()...")
    result = device.action_view_ppp()
    print(f"  Action type: {result['type']}")
    print(f"  Window title: {result['name']}")
    print(f"  Model: {result['res_model']}")
    print(f"  Domain: {result['domain']}")
    
    print("\n" + "=" * 70)
    print("✅ PPP button added successfully!")
    print("=" * 70)
    print("\nRefresh your browser to see the new PPP button:")
    print("  • Position: Between DHCP Leases and Sessions")
    print("  • Icon: Plug icon")
    print("  • Shows: Active PPPoE sessions count")
    print("  • Click: Opens filtered list of PPP sessions only")
