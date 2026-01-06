/** @odoo-module **/

import { GraphController } from "@web/views/graph/graph_controller";
import { patch } from "@web/core/utils/patch";

// Auto-refresh interval (5 seconds)
const REFRESH_INTERVAL = 5000;

patch(GraphController.prototype, {
  setup() {
    super.setup();
    this._autoRefreshInterval = null;

    // Start auto-refresh for MikroTik monitoring graphs
    if (this.props.resModel === "mikrotik.metric.point") {
      this._startAutoRefresh();
    }
  },

  _startAutoRefresh() {
    // Clear existing interval if any
    if (this._autoRefreshInterval) {
      clearInterval(this._autoRefreshInterval);
    }

    // Set up new interval to reload graph data
    this._autoRefreshInterval = setInterval(async () => {
      try {
        // Reload data using the model's load method
        if (this.model && typeof this.model.load === "function") {
          await this.model.load();
        }
      } catch (error) {
        // Silent fail - continue trying on next interval
        console.debug("MikroTik graph refresh:", error.message || "skipped");
      }
    }, REFRESH_INTERVAL);
  },

  onWillUnmount() {
    // Clean up interval when component is destroyed
    if (this._autoRefreshInterval) {
      clearInterval(this._autoRefreshInterval);
      this._autoRefreshInterval = null;
    }
    if (super.onWillUnmount) {
      super.onWillUnmount();
    }
  },
});
