#!/usr/bin/env python3
"""
Create Sample Metric Data for Testing Graphs
Generates realistic-looking time-series data for graph visualization testing
"""

import sys
import random
from datetime import datetime, timedelta
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import odoo
from odoo import api, SUPERUSER_ID

# Connect to database
dbname = 'odoo'
registry = odoo.registry(dbname)

print("=" * 70)
print("GENERATING SAMPLE METRIC DATA FOR GRAPH TESTING")
print("=" * 70)

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    Device = env['mikrotik.device']
    MetricCatalog = env['mikrotik.metric.catalog']
    MetricPoint = env['mikrotik.metric.point']
    
    # Get or create test device
    device = Device.search([('collection_enabled', '=', True)], limit=1)
    if not device:
        device = Device.search([], limit=1)
        if not device:
            print("\n❌ No devices found! Please create a device first.")
            sys.exit(1)
    
    print(f"\n📡 Using device: {device.name} (ID: {device.id})")
    
    # Get metrics to populate
    metrics_to_generate = {
        'iface.rx_bps': {'base': 50000000, 'variance': 20000000, 'interface': 'ether1'},  # 50 Mbps avg
        'iface.tx_bps': {'base': 30000000, 'variance': 15000000, 'interface': 'ether1'},  # 30 Mbps avg
        'system.cpu.load_pct': {'base': 35, 'variance': 15, 'interface': None},  # 35% avg CPU
        'system.memory.used_pct': {'base': 60, 'variance': 10, 'interface': None},  # 60% avg RAM
        'firewall.connection_count': {'base': 5000, 'variance': 2000, 'interface': None},  # 5000 connections
        'ppp.active_sessions': {'base': 250, 'variance': 50, 'interface': None},  # 250 PPPoE users
        'dhcp.active_leases': {'base': 180, 'variance': 30, 'interface': None},  # 180 DHCP leases
    }
    
    # Generate data for last 1 hour (every 5 seconds = 720 points per metric)
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    interval_seconds = 5
    total_points = int(3600 / interval_seconds)  # 720 points
    
    print(f"\n⏱️  Generating {total_points} data points per metric...")
    print(f"   Time range: {start_time.strftime('%H:%M:%S')} to {now.strftime('%H:%M:%S')}")
    
    points_created = 0
    
    for metric_key, config in metrics_to_generate.items():
        # Get or create metric catalog entry
        metric = MetricCatalog.search([('key', '=', metric_key)], limit=1)
        if not metric:
            print(f"   ⚠️  Metric {metric_key} not found in catalog, skipping...")
            continue
        
        print(f"\n   📈 Generating {metric.name}...")
        
        # Generate realistic time-series with trends
        current_value = config['base']
        
        for i in range(total_points):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            
            # Add some realistic variation
            # - Random walk for smooth transitions
            # - Cyclical pattern (sine wave)
            # - Random spikes
            
            # Random walk component
            change = random.uniform(-config['variance'] * 0.1, config['variance'] * 0.1)
            current_value += change
            
            # Keep within reasonable bounds
            min_value = config['base'] - config['variance']
            max_value = config['base'] + config['variance']
            current_value = max(min_value, min(max_value, current_value))
            
            # Add cyclical pattern (10-minute cycle)
            import math
            cycle_component = config['variance'] * 0.3 * math.sin(i * 2 * math.pi / 120)
            
            # Occasional spike (5% chance)
            spike = 0
            if random.random() < 0.05:
                spike = config['variance'] * 0.5
            
            final_value = max(0, current_value + cycle_component + spike)
            
            # Create metric point
            MetricPoint.create({
                'device_id': device.id,
                'metric_id': metric.id,
                'interface_name': config['interface'],
                'ts_collected': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'value_float': final_value,
                'value_text': f"{final_value:.2f}",
            })
            
            points_created += 1
            
            # Show progress every 100 points
            if (i + 1) % 100 == 0:
                progress = (i + 1) / total_points * 100
                print(f"      Progress: {progress:.0f}% ({i+1}/{total_points})", end='\r')
        
        print(f"      ✅ Complete: {total_points} points")
    
    cr.commit()
    
    print("\n" + "=" * 70)
    print("SAMPLE DATA GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n✅ Created {points_created} metric points")
    print(f"📊 Device: {device.name}")
    print(f"⏱️  Time range: Last 1 hour ({total_points} points per metric)")
    print(f"\n💡 Now open the device and click 'Monitoring Graphs' to see beautiful charts!")
    print("=" * 70)
