#!/usr/bin/env python3
"""List all databases and check for mikrotik devices"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

# List all databases
try:
    dbs = odoo.service.db.list_dbs(True)
    print(f"Available databases: {dbs}")
    
    for db_name in dbs:
        print(f"\n{'='*70}")
        print(f"DATABASE: {db_name}")
        print(f"{'='*70}")
        
        try:
            registry = odoo.registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                if 'mikrotik.device' not in env:
                    print("  ⚠️  mikrotik_monitoring module not installed")
                    continue
                
                Device = env['mikrotik.device']
                MetricPoint = env['mikrotik.metric.point']
                
                all_devices = Device.search([])
                enabled_devices = Device.search([('collection_enabled', '=', True)])
                
                print(f"  Total devices: {len(all_devices)}")
                print(f"  Collection enabled: {len(enabled_devices)}")
                
                for device in all_devices:
                    print(f"\n  📱 {device.name} (ID: {device.id})")
                    print(f"     Host: {device.host}")
                    print(f"     Collection: {'✅ ENABLED' if device.collection_enabled else '❌ DISABLED'}")
                    print(f"     State: {device.state}")
                    print(f"     Last Seen: {device.last_seen or 'Never'}")
                    
                    # Check metrics
                    metric_count = MetricPoint.search_count([('device_id', '=', device.id)])
                    print(f"     Total metrics: {metric_count}")
                    
                    if metric_count > 0:
                        latest = MetricPoint.search([('device_id', '=', device.id)], 
                                                   order='ts_collected desc', limit=1)
                        print(f"     Latest metric: {latest.ts_collected}")
                
        except Exception as e:
            print(f"  Error accessing database: {e}")
            
except Exception as e:
    print(f"Error listing databases: {e}")
