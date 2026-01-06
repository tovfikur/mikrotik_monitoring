#!/usr/bin/env python3
"""Debug collector internals"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    from odoo.addons.mikrotik_monitoring.collector import async_collector
    
    collector_service = async_collector.get_collector()
    
    if not collector_service:
        print("❌ Collector service is None!")
    else:
        print(f"✅ Collector service exists")
        print(f"   Running: {collector_service.running}")
        print(f"   Database: {collector_service.dbname}")
        
        # Access the collectors dictionary
        print(f"\n📊 Collectors registered:")
        with collector_service._lock:
            print(f"   Total: {len(collector_service._collectors)}")
            for device_id, coll in collector_service._collectors.items():
                print(f"   Device {device_id}: {coll.config.get('host')}")
        
        if len(collector_service._collectors) == 0:
            print(f"\n⚠️  No collectors registered!")
            print(f"   This means devices failed to connect.")
            print(f"\n   Forcing reload...")
            
            # Force reload
            collector_service._reload_collectors(env)
            
            with collector_service._lock:
                print(f"\n   After reload: {len(collector_service._collectors)} collectors")
                for device_id, coll in collector_service._collectors.items():
                    print(f"   Device {device_id}: {coll.config.get('host')}")
