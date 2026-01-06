# MikroTik Monitoring - Real-Time Graphs Guide

## ✅ What Was Fixed

### 1. Time Filter Issues

**Problem:** Graphs were showing data aggregated by month instead of showing recent real-time data.

**Solution:**

- Fixed time filters to use `datetime.datetime.now()` instead of `context_today()`
- Filters now correctly show data from:
  - **Last Hour** - Real-time monitoring (default)
  - **Last 24 Hours** - Daily trends
  - **Last Week** - Weekly analysis

### 2. Graph Grouping

**Problem:** Metrics were being aggregated together instead of showing as separate time-series lines.

**Solution:**

- Added proper grouping: `ts_collected` as X-axis (row), `metric_id` as separate lines (col)
- Added minute/hour/day grouping options in the "Group By" menu
- Each metric now appears as its own line on the graph

### 3. Auto-Refresh for Real-Time Updates

**Problem:** Graphs were static and didn't update automatically like MikroTik graphs.

**Solution:**

- Added JavaScript auto-refresh functionality
- Graphs now automatically reload every **5 seconds**
- Data updates in real-time without manual page refresh
- Auto-refresh only applies to MikroTik monitoring graphs

## 📊 How to Use the Graphs

### Opening Graphs

1. Go to **MikroTik Monitoring** menu
2. Open **Devices**
3. Click on your device (e.g., "Kendroo")
4. Click the **"📊 Monitoring Graphs"** button at the top

### Available Graphs

1. **1️⃣ Interface Traffic** - RX/TX bandwidth per interface
2. **2️⃣ Interface Errors & Drops** - Network quality indicators
3. **3️⃣ CPU Usage** - Router CPU load
4. **4️⃣ Memory Usage** - RAM utilization
5. **5️⃣ Uptime** - System uptime tracking
6. **6️⃣ Temperature** - Hardware temperature monitoring
7. **7️⃣ Active Connections** - Firewall connection count
8. **8️⃣ DHCP Leases** - Active DHCP clients
9. **9️⃣ PPPoE/Hotspot Sessions** - Active user sessions
10. **🔟 Network Latency** - Ping response times
11. **1️⃣1️⃣ Queue Usage** - Bandwidth queue utilization
12. **1️⃣2️⃣ Wireless Clients** - Connected wireless clients

### Graph Features

- **Real-Time Updates:** Graphs refresh every 5 seconds automatically
- **Time Range Selection:** Use filters to view Last Hour, 24 Hours, or Week
- **Multiple Metrics:** Each metric shows as a separate colored line
- **Interactive:** Hover over lines to see exact values
- **Zoom:** Click and drag to zoom into specific time ranges

### Customizing Views

**Group By Options:**

- **Minute** - Show data points every minute (best for real-time)
- **Hour** - Hourly aggregation
- **Day** - Daily summaries
- **Metric** - Separate lines per metric type
- **Interface** - Separate lines per network interface

**To change grouping:**

1. Click "Group By" in the search bar
2. Select your preferred grouping
3. Can combine multiple groupings (e.g., Minute + Metric)

## 🔧 Technical Details

### Data Collection

- **Frequency:** Every 5 seconds for real-time metrics (T0)
- **Storage:** Time-series data in `mikrotik.metric.point` table
- **Retention:** Data retained based on tier (T0, T1, T2, T3)

### Auto-Refresh Mechanism

- **File:** `static/src/js/graph_auto_refresh.js`
- **Interval:** 5000ms (5 seconds)
- **Scope:** Only applies to `mikrotik.metric.point` model
- **Method:** Patches Odoo's GraphController to automatically reload data

### Performance

- Graphs only load visible time range (default: last hour)
- Auto-refresh uses optimized queries with indexed timestamps
- Collector runs independently in background thread

## 📈 Making Graphs Look Like MikroTik

While Odoo's native graph views use line charts, MikroTik uses filled area charts. The current implementation provides:

✅ **Time-series line charts** with multiple metrics
✅ **Real-time auto-refresh** every 5 seconds
✅ **Interactive hovering** for exact values
✅ **Color-coded metrics** for easy identification

To get even closer to MikroTik's appearance, you could:

1. Use custom Chart.js implementation for filled area charts
2. Add gradient fills below lines
3. Customize colors to match MikroTik's palette

The current solution balances MikroTik-like functionality with Odoo's native capabilities.

## 🚀 Verification

To verify everything is working:

1. **Check Collector Status:**

   ```bash
   docker exec odoo-odoo-1 python3 /mnt/extra-addons/mikrotik_monitoring/monitor_qwer_collection.py
   ```

   - Should show "+28 new metrics every 5 seconds"

2. **Check Device State:**

   - Open your device
   - State should be "UP"
   - Last Seen should be "a few seconds ago"

3. **Check Graphs:**
   - Open "Interface Traffic" graph
   - Should see RX/TX lines updating every 5 seconds
   - Hover over lines to see values

## 📝 Troubleshooting

**Graphs not showing data:**

- Verify collector is running (check Device form "Collector Status")
- Ensure "Last Hour" filter is active
- Check that device has `collection_enabled = True`

**Auto-refresh not working:**

- Clear browser cache
- Refresh the page (Ctrl+F5)
- Check browser console for JavaScript errors

**Data looks wrong:**

- Check time filter selection
- Verify correct "Group By" options
- Ensure device is connected and accessible

**Collector not running:**

- Click "Start Collector" button on device form
- Check Odoo logs for errors
- Verify RouterOS API credentials

## 🎯 Best Practices

1. **Use "Last Hour" filter** for real-time monitoring
2. **Group by Minute** for detailed 5-second granularity
3. **Open specific graph types** instead of "All Graphs" for better performance
4. **Monitor multiple graphs** by opening in separate tabs
5. **Let auto-refresh work** - avoid manual refreshing

---

**Note:** The auto-refresh feature is optimized for MikroTik monitoring and only activates on metric graphs. Regular Odoo views maintain their normal behavior.
