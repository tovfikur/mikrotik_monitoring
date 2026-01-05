#!/usr/bin/env python3
"""
Test Monitoring Graphs
Verifies that all graph views and actions are accessible
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
    print("MONITORING GRAPHS TEST")
    print("=" * 60)
    
    # Get device
    Device = env['mikrotik.device']
    devices = Device.search([], limit=1)
    
    if not devices:
        print("\n❌ No devices found! Please create a device first.")
        sys.exit(1)
    
    device = devices[0]
    print(f"\n✅ Testing with device: {device.name}")
    
    # Test graph actions
    graph_actions = [
        'action_mikrotik_all_graphs',
        'action_mikrotik_traffic_graph',
        'action_mikrotik_errors_graph',
        'action_mikrotik_cpu_graph',
        'action_mikrotik_ram_graph',
        'action_mikrotik_connections_graph',
        'action_mikrotik_pppoe_graph',
        'action_mikrotik_dhcp_graph',
        'action_mikrotik_health_graph',
    ]
    
    print("\n" + "=" * 60)
    print("GRAPH ACTIONS")
    print("=" * 60)
    
    Action = env['ir.actions.act_window']
    for action_name in graph_actions:
        try:
            action_ref = env.ref(f'mikrotik_monitoring.{action_name}')
            print(f"✅ {action_name}: {action_ref.name}")
        except Exception as e:
            print(f"❌ {action_name}: NOT FOUND")
    
    # Test metric catalog
    print("\n" + "=" * 60)
    print("METRIC CATALOG")
    print("=" * 60)
    
    Catalog = env['mikrotik.metric.catalog']
    metric_keys = [
        'system.cpu.load_pct',
        'system.memory.used_pct',
        'iface.rx_bps',
        'iface.tx_bps',
        'iface.rx_error',
        'iface.tx_error',
        'firewall.connection_count',
        'ppp.active_sessions',
        'dhcp.active_leases',
        'system.health.temperature',
    ]
    
    for key in metric_keys:
        metric = Catalog.search([('key', '=', key)], limit=1)
        if metric:
            print(f"✅ {key}: {metric.name}")
        else:
            print(f"❌ {key}: NOT IN CATALOG")
    
    # Test metric point model
    print("\n" + "=" * 60)
    print("METRIC POINT MODEL")
    print("=" * 60)
    
    MetricPoint = env['mikrotik.metric.point']
    point_count = MetricPoint.search_count([('device_id', '=', device.id)])
    print(f"📊 Total metric points for {device.name}: {point_count}")
    
    if point_count > 0:
        latest = MetricPoint.search([('device_id', '=', device.id)], limit=5, order='ts_collected desc')
        print(f"\n📈 Latest 5 metrics:")
        for point in latest:
            print(f"   - {point.metric_id.key}: {point.value_float} @ {point.ts_collected}")
    else:
        print("\n⚠️  No metrics collected yet. Enable collection on device and wait.")
    
    # Test menu
    print("\n" + "=" * 60)
    print("MENU ITEMS")
    print("=" * 60)
    
    Menu = env['ir.ui.menu']
    menu_graphs = Menu.search([('name', '=', '📊 Monitoring Graphs')], limit=1)
    if menu_graphs:
        print(f"✅ Monitoring Graphs menu: {menu_graphs.complete_name}")
    else:
        print("❌ Monitoring Graphs menu: NOT FOUND")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED!")
    print("=" * 60)
    print("\n💡 To view graphs in Odoo:")
    print("   1. Open a device form view")
    print("   2. Click the 'Monitoring Graphs' button (chart icon)")
    print("   3. Or go to: MikroTik Monitoring > Monitoring > 📊 Monitoring Graphs")
    print("   4. Enable collection on device to start gathering metrics\n")
