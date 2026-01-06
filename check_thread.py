#!/usr/bin/env python3
"""Check if collector thread is alive"""
import sys
import threading
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

dbname = 'qwer'
registry = odoo.registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    from odoo.addons.mikrotik_monitoring.collector import async_collector
    
    collector = async_collector.get_collector()
    
    if collector:
        print(f"Collector DB: {collector.dbname}")
        print(f"Collector Running flag: {collector.running}")
        
        # Check all threads
        print(f"\n🧵 Active threads:")
        for thread in threading.enumerate():
            print(f"   - {thread.name} (alive: {thread.is_alive()}, daemon: {thread.daemon})")
            
            if 'collector' in thread.name.lower() or 'mikrotik' in thread.name.lower():
                print(f"     ⭐ This looks like the collector thread!")
        
        # Check collector internals
        print(f"\n📊 Collectors registered: {len(collector._collectors)}")
        
        if len(collector._collectors) > 0:
            # Manually trigger collection
            print(f"\n🔨 Manually triggering collection...")
            try:
                collector._collect_all(env)
                print(f"   ✅ Collection triggered successfully!")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
