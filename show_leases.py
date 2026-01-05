#!/usr/bin/env python3
"""Show DHCP lease details"""
import odoo
from odoo import api, SUPERUSER_ID

registry = odoo.registry('qwer')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Device = env['mikrotik.device']
    Lease = env['mikrotik.lease']
    Session = env['mikrotik.session']
    
    device = Device.search([('host', '=', '192.168.50.1')], limit=1)
    
    print("=" * 70)
    print(f"DHCP LEASES FOR {device.name}")
    print("=" * 70)
    
    leases = Lease.search([('device_id', '=', device.id)], order='address')
    
    print(f"\nTotal Leases: {len(leases)}")
    print(f"\nStatus breakdown:")
    
    status_count = {}
    for lease in leases:
        status_count[lease.status] = status_count.get(lease.status, 0) + 1
    
    for status, count in status_count.items():
        print(f"  {status}: {count}")
    
    print(f"\n{'IP Address':<15} {'MAC Address':<17} {'Hostname':<25} {'Server':<10} Status")
    print("-" * 85)
    
    for lease in leases:
        hostname = (lease.hostname or "(no hostname)")[:24]
        server = (lease.server or "")[:9]
        print(f"{lease.address:<15} {lease.mac_address:<17} {hostname:<25} {server:<10} {lease.status}")
    
    # Check PPP sessions too
    sessions = Session.search([('device_id', '=', device.id)])
    print(f"\n\nPPP Sessions: {len(sessions)}")
    
    if sessions:
        print(f"\n{'Username':<20} {'Address':<15} {'Uptime':<15} Status")
        print("-" * 60)
        for sess in sessions[:10]:
            print(f"{sess.name:<20} {sess.address or 'N/A':<15} {sess.uptime_display or 'N/A':<15} {'Active' if sess.is_active else 'Inactive'}")
    
    print("\n" + "=" * 70)
    print("✅ Data available in Odoo UI:")
    print("   MikroTik → Devices → Kendroo → DHCP Leases tab")
    print("   MikroTik → Devices → Kendroo → Sessions tab")
    print("=" * 70)
