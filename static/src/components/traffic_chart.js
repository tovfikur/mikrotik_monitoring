/** @odoo-module **/

import {
  Component,
  onWillStart,
  onMounted,
  onWillUnmount,
  useRef,
  useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Professional ISP-Style Traffic Monitoring Chart
 *
 * Features:
 * - Real-time updates every 5 seconds
 * - Time-series visualization with Chart.js
 * - Multi-interface support with color coding
 * - Zoom and pan capabilities
 * - Filled area charts (ISP style)
 * - Dynamic time range selection
 */
class TrafficChart extends Component {
  setup() {
    this.orm = useService("orm");
    this.chartCanvas = useRef("chartCanvas");

    this.state = useState({
      loading: true,
      timeRange: 1800, // Default 30 minutes
      lastUpdate: null,
      deviceName: "All Devices",
      autoRefresh: true,
      selectedInterface: "",
      metricFilter: "both",
      interfaces: [],
      stats: null,
      showLegend: true,
      smoothness: 0.8, // Chart curve smoothness (0=bumpy, 1=very smooth)
    });

    this.chart = null;
    this.refreshInterval = null;
    this.chartJsLoaded = false;
    this.rawData = null; // Store raw data for filtering

    // Get device_id from props context
    this.deviceId = this.props.action?.context?.device_id || null;

    console.log("TrafficChart initialized with device_id:", this.deviceId);

    onWillStart(async () => {
      await this.loadChartJs();

      // Load device name if device_id is provided
      if (this.deviceId) {
        const devices = await this.orm.searchRead(
          "mikrotik.device",
          [["id", "=", this.deviceId]],
          ["name"]
        );
        if (devices.length > 0) {
          this.state.deviceName = devices[0].name;
        }
      }
    });

    onMounted(async () => {
      // Wait for next tick to ensure canvas is rendered
      await new Promise((resolve) => setTimeout(resolve, 100));
      await this.loadData();
      this.startAutoRefresh();
    });

    onWillUnmount(() => {
      this.stopAutoRefresh();
      if (this.chart) {
        this.chart.destroy();
      }
    });
  }

  /**
   * Load Chart.js library dynamically from CDN
   */
  async loadChartJs() {
    if (window.Chart) {
      console.log("Chart.js already loaded");
      this.chartJsLoaded = true;
      return;
    }

    console.log("Loading Chart.js from CDN...");
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src =
        "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
      script.onload = () => {
        console.log("Chart.js loaded, loading date adapter...");
        // Load date adapter
        const adapter = document.createElement("script");
        adapter.src =
          "https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js";
        adapter.onload = () => {
          console.log("Date adapter loaded successfully");
          this.chartJsLoaded = true;
          resolve();
        };
        adapter.onerror = (err) => {
          console.error("Failed to load date adapter:", err);
          reject(err);
        };
        document.head.appendChild(adapter);
      };
      script.onerror = (err) => {
        console.error("Failed to load Chart.js:", err);
        reject(err);
      };
      document.head.appendChild(script);
    });
  }

  /**
   * Load metric data from Odoo backend
   */
  async loadData() {
    if (!this.chartJsLoaded) {
      console.error("Chart.js not loaded yet");
      return;
    }

    this.state.loading = true;

    try {
      console.log("Loading traffic data...");
      // Calculate time window
      const now = new Date();
      const startTime = new Date(now.getTime() - this.state.timeRange * 1000);

      // Format for Odoo datetime comparison
      const startTimeStr = startTime
        .toISOString()
        .replace("T", " ")
        .slice(0, 19);

      // Fetch traffic metrics (RX, TX, and Ping Latency)
      const domain = [
        ["ts_collected", ">=", startTimeStr],
        [
          "metric_id.key",
          "in",
          ["iface.rx_bps", "iface.tx_bps", "ping.avg_latency_ms"],
        ],
      ];

      // Filter by device if device_id is provided
      if (this.deviceId) {
        domain.push(["device_id", "=", this.deviceId]);
      }

      const fields = [
        "ts_collected",
        "value_float",
        "metric_id",
        "interface_name",
      ];

      const points = await this.orm.searchRead(
        "mikrotik.metric.point",
        domain,
        fields,
        {
          order: "ts_collected ASC",
          limit: 50000, // Safety limit
        }
      );

      // Get metric details
      const metricIds = [...new Set(points.map((p) => p.metric_id[0]))];

      const metrics = await this.orm.searchRead(
        "mikrotik.metric.catalog",
        [["id", "in", metricIds]],
        ["id", "key"]
      );

      // Create lookup map
      const metricMap = Object.fromEntries(metrics.map((m) => [m.id, m.key]));

      // Store raw data with metric keys for filtering/export
      this.rawData = points.map((p) => ({
        ...p,
        metricKey: metricMap[p.metric_id[0]],
      }));

      // Extract unique interfaces for filter dropdown
      const interfaces = [
        ...new Set(points.map((p) => p.interface_name).filter(Boolean)),
      ].sort();
      this.state.interfaces = interfaces;

      // Apply filters to data before processing
      let filteredPoints = this.applyDataFilters(points, metricMap);

      // Calculate statistics
      this.calculateStats(
        filteredPoints.map((p) => ({
          ...p,
          metricKey: metricMap[p.metric_id[0]],
        }))
      );

      // Process data for Chart.js
      const processedData = this.processData(filteredPoints, metricMap);

      // Render or update chart
      if (this.chart) {
        this.updateChart(processedData);
      } else {
        this.renderChart(processedData);
      }

      this.state.lastUpdate = new Date();
    } catch (error) {
      console.error("Error loading traffic data:", error);
    } finally {
      this.state.loading = false;
    }
  }

  /**
   * Process raw metric points into Chart.js datasets
   */
  processData(points, metricMap) {
    // Group by interface and metric type
    const grouped = {};

    for (const point of points) {
      const metricKey = metricMap[point.metric_id[0]];

      // Handle ping latency separately
      if (metricKey === "ping.avg_latency_ms") {
        const key = "Ping Latency";
        if (!grouped[key]) {
          grouped[key] = {
            interfaceName: "Ping",
            metricType: "Latency",
            points: [],
            isPing: true,
          };
        }
        const timestamp = new Date(point.ts_collected.replace(" ", "T") + "Z");
        grouped[key].points.push({
          x: timestamp,
          y: point.value_float || 0,
        });
        continue;
      }

      const interfaceName = point.interface_name || "Unknown";
      const metricType = metricKey.endsWith("rx_bps") ? "RX" : "TX";

      const key = `${interfaceName}|${metricType}`;

      if (!grouped[key]) {
        grouped[key] = {
          interfaceName,
          metricType,
          points: [],
        };
      }

      // Convert to Mbps and parse timestamp
      const timestamp = new Date(point.ts_collected.replace(" ", "T") + "Z");
      const valueMbps = (point.value_float || 0) / 1000000;

      grouped[key].points.push({
        x: timestamp,
        y: valueMbps,
      });
    }

    // Convert to Chart.js datasets
    const datasets = [];
    const sortedKeys = Object.keys(grouped).sort();

    for (const key of sortedKeys) {
      const data = grouped[key];
      const color = data.isPing
        ? "#dc3545"
        : this.getColorForInterface(data.interfaceName, data.metricType);

      datasets.push({
        label: `${data.interfaceName} - ${data.metricType}`,
        data: data.points,
        borderColor: color,
        backgroundColor: data.isPing
          ? "transparent"
          : this.hexToRgba(color, 0.2),
        borderWidth: data.isPing ? 3 : 2,
        fill: data.isPing ? false : true,
        tension: this.state.smoothness,
        cubicInterpolationMode: "monotone",
        pointRadius: 0,
        pointHitRadius: 10,
        yAxisID: data.isPing ? "y1" : "y",
        borderDash: data.isPing ? [5, 5] : [],
      });
    }

    return datasets;
  }

  /**
   * Assign consistent colors to interfaces
   */
  getColorForInterface(interfaceName, metricType) {
    // Predefined color palette (ISP style - professional colors)
    const colors = [
      "#2196F3", // Blue
      "#4CAF50", // Green
      "#FF9800", // Orange
      "#9C27B0", // Purple
      "#F44336", // Red
      "#00BCD4", // Cyan
      "#FFEB3B", // Yellow
      "#795548", // Brown
      "#607D8B", // Blue Grey
      "#E91E63", // Pink
      "#3F51B5", // Indigo
      "#8BC34A", // Light Green
    ];

    // Hash interface name to consistent color
    let hash = 0;
    for (let i = 0; i < interfaceName.length; i++) {
      hash = interfaceName.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colorIndex = Math.abs(hash) % colors.length;
    const baseColor = colors[colorIndex];

    // Make TX slightly darker than RX
    if (metricType === "TX") {
      return this.darkenColor(baseColor, 20);
    }

    return baseColor;
  }

  /**
   * Darken a hex color
   */
  darkenColor(hex, percent) {
    const num = parseInt(hex.slice(1), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) - amt;
    const G = ((num >> 8) & 0x00ff) - amt;
    const B = (num & 0x0000ff) - amt;
    return (
      "#" +
      (
        0x1000000 +
        (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
        (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
        (B < 255 ? (B < 1 ? 0 : B) : 255)
      )
        .toString(16)
        .slice(1)
    );
  }

  /**
   * Convert hex to rgba
   */
  hexToRgba(hex, alpha) {
    const num = parseInt(hex.slice(1), 16);
    const r = (num >> 16) & 255;
    const g = (num >> 8) & 255;
    const b = num & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  /**
   * Render initial Chart.js chart
   */
  async renderChart(datasets) {
    // Wait for canvas element to be available
    let retries = 0;
    while (!this.chartCanvas.el && retries < 20) {
      console.log(`Waiting for canvas element... (attempt ${retries + 1})`);
      await new Promise((resolve) => setTimeout(resolve, 100));
      retries++;
    }

    if (!this.chartCanvas.el) {
      console.error("Canvas element not found after waiting!");
      return;
    }

    if (!window.Chart) {
      console.error("Chart.js not available!");
      return;
    }

    console.log(`Rendering chart with ${datasets.length} datasets`);

    const ctx = this.chartCanvas.el.getContext("2d");

    this.chart = new Chart(ctx, {
      type: "line",
      data: {
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "nearest",
          axis: "x",
          intersect: false,
        },
        plugins: {
          title: {
            display: false, // Title in header now
          },
          legend: {
            display: this.state.showLegend,
            position: "bottom",
            labels: {
              usePointStyle: true,
              boxWidth: 8,
              padding: 15,
              font: {
                size: 11,
                weight: "500",
              },
            },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            titleColor: "#fff",
            bodyColor: "#fff",
            borderColor: "rgba(255, 255, 255, 0.2)",
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            callbacks: {
              label: function (context) {
                const label = context.dataset.label || "";
                const value = context.parsed.y.toFixed(2);
                const unit = label.includes("Latency") ? " ms" : " Mbps";
                return `${label}: ${value}${unit}`;
              },
              title: function (context) {
                const date = new Date(context[0].parsed.x);
                return date.toLocaleString();
              },
            },
          },
          zoom: {
            zoom: {
              wheel: {
                enabled: true,
              },
              pinch: {
                enabled: true,
              },
              mode: "x",
            },
            pan: {
              enabled: true,
              mode: "x",
            },
            limits: {
              x: { min: "original", max: "original" },
            },
          },
        },
        scales: {
          x: {
            type: "time",
            time: {
              displayFormats: {
                second: "HH:mm:ss",
                minute: "HH:mm",
                hour: "MMM dd HH:mm",
                day: "MMM dd",
              },
            },
            title: {
              display: true,
              text: "Time",
              font: {
                size: 12,
                weight: "600",
              },
            },
            ticks: {
              maxRotation: 45,
              minRotation: 0,
              font: {
                size: 10,
              },
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
          y: {
            beginAtZero: true,
            position: "left",
            title: {
              display: true,
              text: "Traffic (Mbps)",
              font: {
                size: 12,
                weight: "600",
              },
            },
            ticks: {
              font: {
                size: 10,
              },
              callback: function (value) {
                return value.toFixed(1) + " Mbps";
              },
            },
            grid: {
              color: "rgba(0, 0, 0, 0.05)",
            },
          },
          y1: {
            position: "right",
            min: 0,
            max: 100,
            title: {
              display: true,
              text: "Latency (ms)",
              font: {
                size: 12,
                weight: "600",
              },
              color: "#dc3545",
            },
            ticks: {
              font: {
                size: 10,
              },
              color: "#dc3545",
              stepSize: 10,
              callback: function (value) {
                return value.toFixed(0) + " ms";
              },
            },
            grid: {
              display: false,
            },
          },
        },
      },
    });
  }

  /**
   * Update existing chart with new data
   */
  updateChart(datasets) {
    if (!this.chart) {
      this.renderChart(datasets);
      return;
    }

    this.chart.data.datasets = datasets;
    this.chart.update("none"); // Update without animation for real-time feel
  }

  /**
   * Start automatic refresh every 5 seconds
   */
  startAutoRefresh() {
    this.stopAutoRefresh(); // Clear any existing interval

    if (!this.state.autoRefresh) return;

    this.refreshInterval = setInterval(() => {
      if (this.state.autoRefresh) {
        this.loadData();
      }
    }, 5000); // 5 second refresh
  }

  /**
   * Stop automatic refresh
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Change smoothness and update chart
   */
  changeSmoothness(newValue) {
    const newSmoothness = parseFloat(newValue);
    console.log("Smoothness changed to:", newSmoothness);
    this.state.smoothness = newSmoothness;
    
    if (this.chart && this.rawData) {
      const metricMap = {};
      this.rawData.forEach((p) => {
        metricMap[p.metric_id[0]] = p.metricKey;
      });
      let filteredData = this.applyDataFilters(
        this.rawData.map((p) => ({
          ...p,
          metric_id: [p.metric_id[0]],
        })),
        metricMap
      );
      const processedData = this.processData(filteredData, metricMap);
      
      // Destroy old chart and render new one to apply tension changes
      this.chart.destroy();
      this.chart = null;
      
      // Wait a tick for canvas to be ready
      setTimeout(() => {
        this.renderChart(processedData);
      }, 0);
    }
  }

  /**
   * Change time range and reload data
   */
  async changeTimeRange(seconds) {
    this.state.timeRange = seconds;
    await this.loadData();
  }

  // Event handlers for template buttons
  changeTimeRange300() {
    this.changeTimeRange(300);
  }

  changeTimeRange1800() {
    this.changeTimeRange(1800);
  }

  changeTimeRange3600() {
    this.changeTimeRange(3600);
  }

  changeTimeRange86400() {
    this.changeTimeRange(86400);
  }

  changeTimeRange604800() {
    this.changeTimeRange(604800);
  }

  changeTimeRange2592000() {
    this.changeTimeRange(2592000);
  }

  /**
   * Toggle auto-refresh on/off
   */
  toggleAutoRefresh() {
    this.state.autoRefresh = !this.state.autoRefresh;
    if (this.state.autoRefresh) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
  }

  /**
   * Manually refresh data now
   */
  async refreshNow() {
    await this.loadData();
  }

  /**
   * Reset chart zoom to default
   */
  resetZoom() {
    if (this.chart) {
      this.chart.resetZoom();
    }
  }

  /**
   * Toggle legend visibility
   */
  toggleLegend() {
    this.state.showLegend = !this.state.showLegend;
    if (this.chart) {
      this.chart.options.plugins.legend.display = this.state.showLegend;
      this.chart.update();
    }
  }

  /**
   * Export chart data to CSV
   */
  exportData() {
    if (!this.rawData) return;

    let csv = "Timestamp,Interface,Metric,Value (Mbps)\n";

    this.rawData.forEach((point) => {
      const timestamp = point.ts_collected;
      const iface = point.interface_name || "Unknown";
      const metric = point.metricKey;
      const value = (point.value_float / 1000000).toFixed(3);
      csv += `${timestamp},${iface},${metric},${value}\n`;
    });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `traffic_${this.state.deviceName}_${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * Apply filters to raw data points (used during initial load and manual filter changes)
   */
  applyDataFilters(points, metricMap) {
    return points.filter((point) => {
      const interfaceName = point.interface_name;
      const metricKey = metricMap[point.metric_id[0]];

      // Interface filter
      if (
        this.state.selectedInterface &&
        interfaceName !== this.state.selectedInterface
      ) {
        return false;
      }

      // Metric filter
      if (this.state.metricFilter === "rx" && !metricKey.includes("rx")) {
        return false;
      }
      if (this.state.metricFilter === "tx" && !metricKey.includes("tx")) {
        return false;
      }

      return true;
    });
  }

  /**
   * Apply interface and metric filters (called when user changes filters)
   */
  applyFilters() {
    if (!this.rawData) return;

    // Build metricMap from rawData
    const metricMap = {};
    this.rawData.forEach((p) => {
      metricMap[p.metric_id[0]] = p.metricKey;
    });

    // Apply filters
    let filteredData = this.applyDataFilters(
      this.rawData.map((p) => ({
        ...p,
        metric_id: [p.metric_id[0]],
      })),
      metricMap
    );

    const processedData = this.processData(filteredData, metricMap);
    this.updateChart(processedData);
    this.calculateStats(
      filteredData.map((p) => ({
        ...p,
        metricKey: metricMap[p.metric_id[0]],
      }))
    );
  }

  /**
   * Calculate statistics from data - show recent averages (last 30 seconds)
   */
  calculateStats(points) {
    const interfaces = new Set();

    // Get recent points (last 30 seconds) for current traffic stats
    const now = new Date();
    const thirtySecondsAgo = new Date(now.getTime() - 30000);

    const recentPoints = points.filter((point) => {
      const pointTime = new Date(point.ts_collected.replace(" ", "T") + "Z");
      return pointTime >= thirtySecondsAgo;
    });

    let totalRx = 0;
    let totalTx = 0;
    let rxCount = 0;
    let txCount = 0;

    points.forEach((point) => {
      interfaces.add(point.interface_name);
    });

    // Use recent points for current traffic calculation
    recentPoints.forEach((point) => {
      if (point.metricKey.includes("rx")) {
        totalRx += point.value_float || 0;
        rxCount++;
      } else {
        totalTx += point.value_float || 0;
        txCount++;
      }
    });

    this.state.stats = {
      interfaceCount: interfaces.size,
      totalRx: rxCount > 0 ? totalRx / rxCount : 0,
      totalTx: txCount > 0 ? totalTx / txCount : 0,
      pointCount: points.length,
    };
  }

  /**
   * Format time for display
   */
  formatTime(date) {
    if (!date) return "";
    return date.toLocaleTimeString();
  }

  /**
   * Format bandwidth value
   */
  formatBandwidth(bps) {
    if (!bps) return "0 bps";
    const mbps = bps / 1000000;
    if (mbps >= 1000) {
      return (mbps / 1000).toFixed(2) + " Gbps";
    }
    return mbps.toFixed(2) + " Mbps";
  }
}

TrafficChart.template = "mikrotik_monitoring.TrafficChart";

// Register as client action
registry
  .category("actions")
  .add("mikrotik_monitoring.TrafficChart", TrafficChart);

export default TrafficChart;
