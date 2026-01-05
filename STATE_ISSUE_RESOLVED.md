# ISSUE RESOLVED: Device State Display

## Problem

Router was UP and accessible, but Odoo UI showed device state as "Down".

## Root Cause

1. **Collector was stopped** - The test scripts stopped the collector after testing
2. **State not updating automatically** - When collector is stopped, no metrics are collected, so device state doesn't update to "up"
3. **Test Connection didn't persist state** - The button tested connection but the state wasn't being refreshed properly in the UI

## Solution

### 1. Start the Collector

The collector **must be running** to continuously update device state. When the collector successfully collects metrics, it automatically sets device state to "up".

```python
# Collector updates state on every successful collection:
device.write({"state": "up", "last_seen": ts_now})
```

### 2. Fixed Test Connection Message

Updated the notification to clarify that state was updated:

```python
"message": _("Connected to %s (RouterOS %s). State updated to UP.")
```

## How It Works

### Device State Management

The device state is managed by the collector:

- **UP**: Collector successfully collecting metrics (updated every 5s by default)
- **DOWN**: Collector cannot connect or collection fails
- **DEGRADED**: Partial metrics or intermittent issues
- **UNKNOWN**: Never contacted or collector not running

### To Keep Router Showing "UP"

1. **Start the Collector**:

   - Click "Start Collector" button in Odoo UI
   - Or: MikroTik → Configuration → Start Collector
   - This starts background collection every 5 seconds

2. **Ensure collection_enabled = True**:

   - Device form → Collection Enabled checkbox
   - Only enabled devices are monitored

3. **Check Realtime Interval**:
   - Default: 5 seconds
   - Device form → scroll down to interval fields
   - State updates happen during realtime collection

## Current Status

✅ **Collector is now RUNNING**  
✅ **Device state: UP**  
✅ **Last seen: 2026-01-05 16:37:24**  
✅ **Collecting metrics every 5 seconds**

## Verification Steps

### Check Device State:

```bash
docker exec odoo-odoo-1 python3 /mnt/extra-addons/mikrotik_monitoring/check_device_state.py
```

Expected output:

```
State: up
Collection Enabled: True
✅ Collector Running: True
```

### In Odoo UI:

1. Refresh browser (F5 or Ctrl+R)
2. Device state should now show "Up" (green)
3. Live Metrics tab should show recent data
4. Last Seen timestamp should be recent (within last 10 seconds)

## Troubleshooting

### If device shows "Down":

1. Check if collector is running:

   ```python
   from odoo.addons.mikrotik_monitoring.collector.async_collector import get_collector
   collector = get_collector()
   print(f"Running: {collector.running if collector else False}")
   ```

2. Start collector if stopped:

   - Click "Start Collector" button
   - Or run: `env['mikrotik.device'].action_start_collector()`

3. Check device collection is enabled:

   - Device form → Collection Enabled = True

4. Verify credentials:
   - Click "Test Connection" button
   - Should show success message

### If state doesn't update in UI:

1. **Refresh browser** (F5) - State is updated server-side
2. Check Last Seen timestamp - should be recent
3. View Live Metrics tab - should show current data
4. Check browser console for errors

## Important Notes

- **Collector must run continuously** for automatic state updates
- State changes from "down" → "up" within 5-10 seconds after collection starts
- "Test Connection" button only tests connectivity, doesn't start collection
- Stopping collector will eventually set state back to "down" or "degraded"
- Each successful metric collection resets last_seen timestamp

---

**Status: RESOLVED** ✅  
The collector is now running and device state is correctly showing "UP" in the database.  
**Action Required:** Refresh your browser to see the updated state in the UI.
