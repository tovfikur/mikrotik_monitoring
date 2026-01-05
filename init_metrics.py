#!/usr/bin/env python3
"""
Initialize Metric Catalog
Creates all default metric definitions
"""

import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

# Connect to database
dbname = 'odoo'
registry = odoo.registry(dbname)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    print("=" * 60)
    print("INITIALIZING METRIC CATALOG")
    print("=" * 60)
    
    Catalog = env['mikrotik.metric.catalog']
    
    # Initialize default metrics
    Catalog.init_default_metrics()
    
    cr.commit()
    
    # Count metrics
    total = Catalog.search_count([])
    print(f"\n✅ Metric catalog initialized")
    print(f"📊 Total metrics: {total}")
    
    # Show sample metrics by category
    print("\n" + "=" * 60)
    print("METRICS BY CATEGORY")
    print("=" * 60)
    
    categories = Catalog.read_group(
        [], 
        ['category'], 
        ['category']
    )
    
    for cat in categories:
        category_name = dict(Catalog._fields['category'].selection).get(cat['category'], cat['category'])
        count = cat['category_count']
        print(f"\n{category_name}: {count} metrics")
        
        metrics = Catalog.search([('category', '=', cat['category'])], limit=5)
        for metric in metrics:
            print(f"  - {metric.key} ({metric.unit})")
    
    print("\n" + "=" * 60)
    print("INITIALIZATION COMPLETED!")
    print("=" * 60)
