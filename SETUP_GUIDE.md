# MikroTik Monitoring - Quick Setup Guide

## ✅ Status: Collector Auto-Started

The async collector is now **running automatically** and will collect metrics every 5 seconds. You just need to configure your devices!

## 📋 Setup Steps

### 1. Add a MikroTik Device

1. Open Odoo and go to: **MikroTik Monitoring > Devices**
2. Click **Create** button
3. Fill in device details:
   - **Name**: e.g., "Main Router"
   - **Host**: IP address or hostname of your MikroTik (e.g., `192.168.88.1`)
   - **Username**: API username (default: `admin`)
   - **Password**: API password
   - **Port**: API port (default: `8728`)

### 2. Test Connection

1. Click the **"Test Connection"** button
2. If successful, you'll see: ✅ **Connection successful**
3. If failed, verify:
   - MikroTik IP/hostname is reachable
   - API service is enabled on MikroTik: `/ip service enable api`
   - Username/password are correct
   - Firewall allows connections on port 8728

### 3. Enable Collection

1. In the device form, go to **"Live Dashboard"** tab
2. Check the box: ☑️ **Collection Enabled**
3. Click **Save**

### 4. Verify Data Collection

Run the monitoring script:

```bash
docker exec odoo-odoo-1 python3 /mnt/extra-addons/mikrotik_monitoring/test_realtime_collection.py
```

You should see:

```
⏰ 18:15:30 - Total metrics: 45 (+15 new)
   Latest metrics:
   • Main Router: interface.traffic.tx = 1234567.00 (2s ago)
   • Main Router: system.cpu.usage = 15.50 (3s ago)
   ✅ Collection is working!
```

### 5. View Graphs

1. Open the device form
2. Click the **"Monitoring Graphs"** button at the top
3. Select any graph to view:
   - Interface Traffic (TX/RX)
   - CPU Usage
   - Memory Usage
   - Active Connections
   - PPPoE Users
   - DHCP Leases
   - Latency & Packet Loss
   - BGP Sessions
   - Queue Throughput
   - Firewall Drops
   - System Health
   - Interface Errors & Drops

Graphs will **auto-refresh** as new metrics arrive every 5 seconds!

---

## 🔧 MikroTik Router Configuration

### Enable API Access

```
/ip service
set api address=192.168.88.0/24 disabled=no port=8728
```

### Create API User (Recommended)

```
/user group add name=api policy=api,read,test
/user add name=odoo_monitor group=api password=your_secure_password
```

### Firewall Rule (if needed)

```
/ip firewall filter
add action=accept chain=input src-address=YOUR_ODOO_IP dst-port=8728 protocol=tcp comment="Odoo Monitoring API"
```

---

## 🎯 Collection Intervals

The collector uses **tiered intervals** for optimal performance:

- **Tier 0 (Realtime)**: Every **5 seconds**
  - Interface traffic
  - CPU/Memory
  - Active connections
- **Tier 1 (Short)**: Every **60 seconds**
  - Interface errors
  - PPPoE users
  - DHCP leases
  - Ping tests
- **Tier 2 (Medium)**: Every **5 minutes**
  - BGP sessions
  - Queue stats
  - Firewall rules
- **Tier 3 (Long)**: Every **1 hour+**
  - System info
  - Hardware details

---

## 🚀 Auto-Start Features

✅ Collector starts automatically when Odoo boots  
✅ Watchdog cron checks every 5 minutes and restarts if needed  
✅ Data stored asynchronously (non-blocking)  
✅ Metrics indexed for fast graph queries

---

## 🐛 Troubleshooting

### Collector Not Running

Check logs:

```bash
docker logs odoo-odoo-1 | grep -i collector
```

Should see:

```
🚀 Auto-starting MikroTik Async Collector for database: odoo
✅ MikroTik Async Collector started successfully for odoo
```

### No Metrics Being Collected

1. Verify device has `collection_enabled=True`
2. Check device state is not `error`
3. Test connection from device form
4. Check MikroTik API logs: `/log print where topics~"api"`

### Graphs Empty

1. Wait 15-30 seconds for initial data collection
2. Refresh the page
3. Check date filter in graph view (default: last 24 hours)
4. Run test script to verify metrics exist in database

---

## 📊 Metrics Available

### System Metrics (40+)

- CPU usage, temperature, voltage
- Memory (total, free, used %)
- Storage (total, free, used %)
- Uptime
- System health score

### Interface Metrics

- Traffic (TX/RX bytes/packets)
- Errors & drops
- Queue drops
- Status (up/down)

### Network Metrics

- Active connections (TCP/UDP)
- Firewall filter stats
- NAT connections
- BGP peers & prefixes

### Service Metrics

- PPPoE active/total users
- DHCP leases used/total
- Queue throughput & packets
- Wireless clients (if applicable)

### Performance Metrics

- Ping latency
- Packet loss %
- Board temperature
- Fan speed

---

## 💡 Next Steps

1. **Add multiple devices** - Monitor your entire network
2. **Configure dashboards** - Pin favorite graphs
3. **Set up alerts** - Get notified of issues (future feature)
4. **Export data** - Use pivot views for analysis

Enjoy real-time MikroTik monitoring! 🎉
