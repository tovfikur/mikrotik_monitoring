# -*- coding: utf-8 -*-

from . import controllers
from . import models

def post_load():
    """Called after module is loaded - start the async collector"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    
    # Import here to avoid circular dependency
    from .collector import async_collector
    
    try:
        # Get the database name from the registry
        import odoo
        target_db = None
        
        # Find the first database with collection-enabled devices
        for db_name in odoo.service.db.list_dbs(True):
            try:
                registry = odoo.registry(db_name)
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    
                    # Check if mikrotik.device model exists (means module is installed)
                    if 'mikrotik.device' in env:
                        Device = env['mikrotik.device']
                        count = Device.search_count([('collection_enabled', '=', True)])
                        
                        if count > 0:
                            _logger.info(f"Found {count} devices with collection enabled in {db_name}")
                            target_db = db_name
                            break
            except Exception as e:
                _logger.warning(f"Could not check {db_name}: {e}")
        
        if target_db:
            _logger.info(f"🚀 Auto-starting MikroTik Async Collector for database: {target_db}")
            async_collector.start_collector(target_db, SUPERUSER_ID)
            _logger.info(f"✅ MikroTik Async Collector started successfully for {target_db}")
        else:
            _logger.info("No databases with collection-enabled devices found")
            
    except Exception as e:
        _logger.error(f"Error in post_load hook: {e}")

