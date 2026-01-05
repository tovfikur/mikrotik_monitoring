/** @odoo-module **/

import {
  Component,
  useState,
  onWillStart,
  onMounted,
  onWillUnmount,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * MikrotikLiveDashboard Component
 *
 * Real-time dashboard widget for MikroTik device monitoring.
 * Subscribes to bus notifications for live metric updates.
 */
export class MikrotikLiveDashboard extends Component {
  static template = "mikrotik_monitoring.LiveDashboard";
  static props = {
    deviceId: { type: Number, optional: true },
    refreshInterval: { type: Number, optional: true },
  };

  setup() {
    this.busService = useService("bus_service");
    this.orm = useService("orm");
    this.notification = useService("notification");

    this.state = useState({
      connected: false,
      lastUpdate: null,
      metrics: {},
      interfaces: [],
      loading: true,
    });

    onWillStart(async () => {
      await this.loadInitialData();
    });

    onMounted(() => {
      this.subscribeToUpdates();
    });

    onWillUnmount(() => {
      this.unsubscribeFromUpdates();
    });
  }

  get deviceId() {
    return this.props.deviceId || this.getDeviceIdFromContext();
  }

  getDeviceIdFromContext() {
    // Try to get device ID from form context
    const formEl = this.el?.closest(".o_form_view");
    if (formEl) {
      const deviceIdEl = formEl.querySelector('[name="id"]');
      if (deviceIdEl) {
        return parseInt(deviceIdEl.value, 10);
      }
    }
    return null;
  }

  async loadInitialData() {
    if (!this.deviceId) {
      this.state.loading = false;
      return;
    }

    try {
      // Load latest metrics snapshot
      const snapshot = await this.orm.call(
        "mikrotik.metric.latest",
        "get_device_snapshot",
        [this.deviceId]
      );

      this.state.metrics = this.processSnapshot(snapshot);

      // Load interfaces
      const interfaces = await this.orm.searchRead(
        "mikrotik.interface",
        [["device_id", "=", this.deviceId]],
        [
          "name",
          "interface_type",
          "is_running",
          "t0_enabled",
          "rx_bps_display",
          "tx_bps_display",
        ]
      );

      this.state.interfaces = interfaces;
      this.state.loading = false;
      this.state.connected = true;
    } catch (error) {
      console.error("Failed to load MikroTik data:", error);
      this.state.loading = false;
      this.notification.add("Failed to load monitoring data", {
        type: "danger",
      });
    }
  }

  processSnapshot(snapshot) {
    const metrics = {};

    for (const item of snapshot) {
      const key = item.interface_name
        ? `${item.metric_key}:${item.interface_name}`
        : item.metric_key;

      metrics[key] = {
        key: item.metric_key,
        interface: item.interface_name,
        value: item.value_display,
        rawValue: item.value_float || item.value_text,
        timestamp: item.ts_last_update,
      };
    }

    return metrics;
  }

  subscribeToUpdates() {
    if (!this.deviceId) return;

    const channel = `mikrotik_monitoring.device.${this.deviceId}`;

    this.busService.addChannel(channel);
    this.busService.addEventListener(
      "notification",
      this.onNotification.bind(this)
    );

    console.log(`Subscribed to MikroTik updates: ${channel}`);
  }

  unsubscribeFromUpdates() {
    this.busService.removeEventListener(
      "notification",
      this.onNotification.bind(this)
    );
  }

  onNotification({ detail: notifications }) {
    for (const { type, payload } of notifications) {
      if (type === "mikrotik_update" && payload.device_id === this.deviceId) {
        this.handleMetricUpdate(payload);
      }
    }
  }

  handleMetricUpdate(payload) {
    const { metrics, ts } = payload;

    for (const [key, value] of Object.entries(metrics)) {
      // Parse interface from key
      let metricKey = key;
      let interfaceName = null;

      if (key.startsWith("iface.") && key.split(".").length > 2) {
        const parts = key.split(".");
        interfaceName = parts[1];
        metricKey = `iface.${parts.slice(2).join(".")}`;
      }

      const stateKey = interfaceName
        ? `${metricKey}:${interfaceName}`
        : metricKey;

      this.state.metrics[stateKey] = {
        key: metricKey,
        interface: interfaceName,
        value: this.formatValue(metricKey, value),
        rawValue: value,
        timestamp: ts,
        updated: true,
      };

      // Clear updated flag after animation
      setTimeout(() => {
        if (this.state.metrics[stateKey]) {
          this.state.metrics[stateKey].updated = false;
        }
      }, 300);
    }

    this.state.lastUpdate = new Date(ts);
  }

  formatValue(key, value) {
    // Format based on metric type
    if (key.includes("_bps") || key.includes("bps")) {
      return this.formatBps(value);
    }
    if (key.includes("_pct") || key.includes("percent")) {
      return `${value.toFixed(1)}%`;
    }
    if (
      key.includes("bytes") ||
      key.includes("memory") ||
      key.includes("disk")
    ) {
      return this.formatBytes(value);
    }
    if (key.includes("temp")) {
      return `${value}°C`;
    }
    if (typeof value === "number") {
      return value.toLocaleString();
    }
    return String(value);
  }

  formatBps(bps) {
    if (bps >= 1000000000) {
      return `${(bps / 1000000000).toFixed(2)} Gbps`;
    }
    if (bps >= 1000000) {
      return `${(bps / 1000000).toFixed(2)} Mbps`;
    }
    if (bps >= 1000) {
      return `${(bps / 1000).toFixed(2)} Kbps`;
    }
    return `${bps} bps`;
  }

  formatBytes(bytes) {
    if (bytes >= 1099511627776) {
      return `${(bytes / 1099511627776).toFixed(2)} TB`;
    }
    if (bytes >= 1073741824) {
      return `${(bytes / 1073741824).toFixed(2)} GB`;
    }
    if (bytes >= 1048576) {
      return `${(bytes / 1048576).toFixed(2)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${bytes} B`;
  }

  get systemMetrics() {
    return Object.values(this.state.metrics).filter(
      (m) => m.key.startsWith("system.") && !m.interface
    );
  }

  get interfaceMetrics() {
    const grouped = {};

    for (const metric of Object.values(this.state.metrics)) {
      if (metric.interface) {
        if (!grouped[metric.interface]) {
          grouped[metric.interface] = [];
        }
        grouped[metric.interface].push(metric);
      }
    }

    return grouped;
  }

  get formattedLastUpdate() {
    if (!this.state.lastUpdate) return "Never";

    const now = new Date();
    const diff = Math.floor((now - this.state.lastUpdate) / 1000);

    if (diff < 5) return "Just now";
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;

    return this.state.lastUpdate.toLocaleTimeString();
  }

  async refreshData() {
    this.state.loading = true;
    await this.loadInitialData();
  }
}

// Register the component
registry.category("view_widgets").add("mikrotik_live_dashboard", {
  component: MikrotikLiveDashboard,
});

export default MikrotikLiveDashboard;
