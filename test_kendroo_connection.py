#!/usr/bin/env python3
"""Test connection to Kendroo device"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

print("=" * 70)
print("TESTING CONNECTION TO KENDROO")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    device = Device.search([('name', '=', 'Kendroo')], limit=1)
    
    if not device:
        print("❌ Device not found!")
        sys.exit(1)
    
    print(f"\n📱 Device: {device.name}")
    print(f"   Host: {device.host}")
    print(f"   Port: {device.api_port}")
    print(f"   Username: {device.username}")
    print(f"   Use TLS: {device.use_ssl}")
    print(f"   State: {device.state}")
    
    # Try to connect
    print(f"\n🔌 Testing connection...")
    
    try:
        from odoo.addons.mikrotik_monitoring.collector.base import MikroTikCollector
        
        collector = MikroTikCollector(
            host=device.host,
            username=device.username,
            password=device.password,
            port=device.api_port or 8728,
            use_ssl=device.use_ssl
        )
        
        # Try to connect
        result = collector.connect()
        
        if result:
            print(f"✅ Connection successful!")
            
            # Try to get system info
            print(f"\n📊 Fetching system resource...")
            try:
                resource = collector.get_system_resources()
                
                if resource:
                    print(f"   Board: {resource.get('board-name', 'N/A')}")
                    print(f"   Version: {resource.get('version', 'N/A')}")
                    print(f"   CPU Load: {resource.get('cpu-load', 'N/A')}%")
                    print(f"   Uptime: {resource.get('uptime', 'N/A')}")
            except Exception as e:
                print(f"   Note: {e}")
            
            collector.disconnect()
            
        else:
            print(f"❌ Connection failed!")
            print(f"   Check credentials and API access")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
