# MikroTik Monitoring for Odoo 17 — Architecture Blueprint (Production)

Date: 2026-01-05

This is a **production-oriented architecture blueprint** (software-architecture level) for building a MikroTik RouterOS monitoring solution integrated with **Odoo 17**.

### Goals (what “professional” means)

- **Reliable** across RouterOS **v6 and v7**, using capability detection and fallbacks.
- **Real-time UX** in Odoo: live views show **only latest** values and update continuously.
- **Optimized**: no Odoo worker blocking, no ORM hot-path inserts, minimal DB contention.
- **Retention**: keep **≥ 90 days** of **1-second** telemetry for selected real-time metrics, while still supporting the full information categories via appropriate (slower) cadences.

### ISP-grade goals (what “ISP-grade” adds)

- **Scale-out architecture**: horizontal scaling for thousands of routers and high interface counts.
- **Multi-tenancy and segmentation**: isolate customers/sites/regions with strict RBAC.
- **High availability**: no single collector instance is a critical point; clear RPO/RTO.
- **Operational excellence**: complete observability (metrics/logs/traces), runbooks, and safe rollouts.
- **Data lifecycle control**: 1s raw for 90 days (required) + rollups for long-term trend queries.

The full list of information categories to cover is in: `requiremetns_monitoring_keypoint _list.txt`.

---

## 1) Requirements interpretation (so it stays reliable and fast)

RouterOS can expose _a very large_ set of information (inventory, configuration, neighbor tables, session tables, etc.). Polling **everything** every second is not a standard practice and will cause performance issues in:

- routers (CPU spikes),
- the collector (connection saturation),
- PostgreSQL (write amplification),
- and Odoo (bus/UI overhead).

**Professional standard:** split collection into tiers, while guaranteeing you can retrieve _every information category_.

### 1.1 Collection tiers (default)

| Tier |            Frequency | Purpose                                   | Examples                                                                                                        |
| ---- | -------------------: | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| T0   |                   1s | Live KPIs + traffic rates + alert signals | CPU%, RAM, disk free, per-interface RX/TX rates, error deltas, conntrack counts, WiFi client counts, LTE signal |
| T1   |                  10s | Fast-changing state tables                | PPP sessions, Hotspot users, BGP/OSPF neighbor state, VRRP state                                                |
| T2   |                  60s | Medium volatility                         | DHCP leases, ARP, DNS cache counters, firewall counters (summary)                                               |
| T3   | 15m–24h or on-change | Inventory/config snapshots                | Packages, license, board/serial, full firewall rules, address lists, routes                                     |

This satisfies:

- **1-second storage for 3 months** (T0 metrics), and
- **“every information” coverage** by collecting the rest via T1–T3 without harming performance.

**Hard requirement is met** by storing T0 at 1s for ≥90 days, while still fetching all categories reliably via tiered scheduling.

### 1.2 Principle: correctness over volume

- Never infer values that RouterOS does not provide.
- Prefer counters + computed rates over sampling “speed” commands.
- Store raw counters when possible; compute rates deterministically.

---

## 2) Reference coverage model (how “every information” is supported)

Your reference list includes 18 categories (system, interfaces, IP, routing protocols, DHCP/DNS, firewall/security, wireless, LTE, hotspot/PPP/VPN, QoS, traffic tools, logging/export, containers, GPS/timing, services, file system, users/access, audit).

### 2.1 Coverage matrix (default mapping)

This mapping is the practical interpretation of “get every information” while remaining safe and scalable.

| Category (from reference)                             |       Default tier | Storage type                | Notes                                                                                       |
| ----------------------------------------------------- | -----------------: | --------------------------- | ------------------------------------------------------------------------------------------- |
| System & hardware                                     |            T0 + T3 | metrics + snapshot          | T0: CPU/RAM/disk/uptime; T3: board/serial/packages/license                                  |
| Interfaces (Ether/SFP/Bridge/VLAN/Bond/Tunnels/VRRP)  |       T0 + T2 + T3 | metrics + snapshot + events | T0: traffic/counters; T2: state tables; events on state change                              |
| IP networking (addr/ARP/ND/IPv6)                      |            T2 + T3 | tables + snapshot           | ARP/ND/leases are tables; addresses/routes as snapshots                                     |
| Routing protocols (OSPF/BGP/RIP/MPLS/VRF)             |            T1 + T3 | state + snapshot + events   | Neighbors/session state (T1); config/snapshots (T3)                                         |
| DHCP/DNS/IP management                                |            T2 + T3 | tables + snapshot           | Leases/tables at T2; static config at T3                                                    |
| Firewall & security (filter/NAT/mangle/raw/conntrack) |       T0 + T2 + T3 | metrics + tables + snapshot | Conn counts can be T0; full rule exports at T3                                              |
| Wireless / WiFi                                       |       T0 + T1 + T3 | metrics + tables + snapshot | Client counts/signal summary at T0; client table at T1                                      |
| LTE / 5G                                              |            T0 + T2 | metrics + table             | Signal metrics at T0; registration/serving cell details at T2                               |
| Hotspot / PPP / VPN                                   |            T1 + T3 | tables + snapshot + events  | Sessions at T1; profile/config at T3                                                        |
| Queues / QoS                                          |            T0 + T3 | metrics + snapshot          | Usage/drops at T0; queue config at T3                                                       |
| Traffic tools (Torch/Sniffer/NetFlow)                 |     on-demand + T2 | on-demand + flow tables     | Torch/sniffer are on-demand (heavy). NetFlow/traffic-flow exported continuously (T2 ingest) |
| Logging & export                                      |          streaming | event/log table             | Prefer syslog streaming; store with retention separate from metrics                         |
| Containers                                            |            T2 + T3 | table + snapshot            | If enabled/supported                                                                        |
| GPS / timing                                          |                 T2 | table/metrics               | If hardware supports                                                                        |
| Services status                                       |                 T2 | table + events              | Track enabled/running and failures                                                          |
| File system                                           |                 T3 | snapshot                    | Inventory-style, not per-second                                                             |
| Users & access control                                |        T3 + events | snapshot + event            | Store users/groups snapshot; login failures as events                                       |
| Audit & compliance                                    | events + snapshots | event + snapshot            | Change logs/exports; keep separate retention policy                                         |

**Coverage is implemented as a plugin catalog**:

- Each category becomes a **Collector Plugin** with:
  - capability checks (RouterOS v6/v7 + package checks),
  - one or more commands to collect (API/REST),
  - a cadence tier (T0–T3),
  - mappings to normalized keys.

This avoids fragile “one giant poller” logic and keeps it maintainable.

### 2.2 End-user scale note (20k subscribers)

With ~20k end-users, some RouterOS tables become **high-cardinality** (large row counts) and must be handled carefully to stay ISP-grade:

- **DHCP leases (20k+)**: do **not** store a full lease snapshot every minute as time-series rows.
  - Store **current state** as an upserted table (one row per active lease).
  - Store **events** on change (lease added/expired/changed) with timestamps.
  - Store **aggregates** every 60s (active lease count, pool utilization, failure counters).
- **PPPoE/Hotspot sessions**: same pattern—current state + change events + periodic aggregates.
- **Connection tracking**: store **counts and summary stats** only; never ingest all conntrack entries at scale.

This preserves “every information category” while preventing DB blow-ups.

---

## 3) Architecture (Collector + Odoo + PostgreSQL)

### 3.1 Why a separate Collector is mandatory (for 1s polling)

Odoo’s built-in cron scheduler is not designed for reliable **1-second** polling loops. Even if forced, it will:

- become inaccurate under load,
- block workers,
- and generate contention in ORM transactions.

**Standard solution:** run a **separate collector service** that:

- polls RouterOS devices on a strict schedule,
- writes telemetry efficiently,
- and notifies Odoo UI for live updates.

### 3.2 Components (and responsibilities)

1. **Odoo 17 Addon (UI + configuration + read APIs)**

- Device inventory and credential references
- Storage schema and retention jobs
- Read-only views (latest + optional history)
- Ingestion endpoints (authenticated) designed for high write throughput
- Realtime fan-out to UI via bus (throttled)

2. **Collector Service (external process; scaling unit)**

- RouterOS API client (works v6 & v7) + optional REST for v7
- Tiered scheduler (T0–T3) with jitter and per-device backoff
- Local buffer (disk/queue) for outage tolerance
- Bulk posts to Odoo ingestion endpoints (JSON batches)
- Health endpoints + metrics for operations

3. **PostgreSQL (optimized for time-series writes)**

- Append-only telemetry partitions (or Timescale hypertables)
- Latest snapshot table for fast UI queries
- Inventory snapshots + events tables

---

## 4) Reliability and performance design (non-functional requirements)

### 4.1 Reliability targets

- Collector tolerates device/API failures without cascading (circuit breaker).
- No data corruption on retries (idempotent ingestion).
- Clock safety: store both `ts_collected` and `ts_received`.

ISP-grade additions:

- **SLO-driven design**: define availability + freshness targets per tier (T0/T1/T2/T3).
- **No silent failure**: every poll failure is recorded (device health timeline) and alertable.

### 4.2 Performance targets

- Odoo workers never run 1s loops.
- High-frequency writes avoid ORM row-by-row inserts.
- DB uses partitions + correct indexes to keep write and read stable.

ISP-grade additions:

- Collector uses **batching** (multi-device concurrent polling) and **bulk ingestion**.
- UI fan-out is **viewer-aware**: publish to bus only for devices currently viewed (or throttle globally).
- Expensive tables (DHCP leases, conntrack entries, BGP routes) are collected on slower tiers or on-demand.

### 4.3 Backpressure and load shedding

- If DB is slow, collector **buffers** and reduces poll frequency (temporary degrade).
- UI updates are **throttled** (e.g., at most 1 update/sec per device).

### 4.4 Availability, RPO/RTO (ISP-grade)

Define these explicitly per environment; typical starting targets:

- **Collector availability**: ≥ 99.9% (service-level).
- **Freshness SLO**:
  - T0: 95% of devices updated within 2 seconds, 99% within 5 seconds.
  - T1/T2/T3: proportional to tier.
- **RPO**: 0–60 seconds (depending on buffer durability and ingestion design).
- **RTO**: 15–60 minutes (replace collector node + replay buffer).

### 4.5 Scaling model (ISP-grade)

- Scale by adding collector instances (horizontal).
- Shard devices by **region/site** (preferred) or by hash of device ID.
- Use bounded concurrency per collector (avoid connection storms).
- Use jitter to avoid synchronized polling (thundering herd).

### 4.6 Multi-tenancy and segmentation (ISP-grade)

Even if you run “single company” today, design for segmentation:

- **Tenant**: customer, region, or NOC domain.
- **Data access**: every device and its telemetry belongs to a tenant.
- **RBAC**: viewer/admin roles per tenant; cross-tenant access only for super-admin.
- **Segmentation boundaries**:
  - UI/permissions in Odoo
  - optional DB-level partitioning by tenant for very large deployments

---

## 5) Data Flow (end-to-end)

### 5.1 Provisioning flow

1. Admin creates a **Device** record in Odoo:
   - IP/DNS, port, timeout, site/group, notes
   - Credentials (username/password or API token, stored securely)
   - Preferred method: RouterOS API (8728/8729) or REST (v7)
2. Admin runs **Connectivity Test** action (server-side):
   - handshake, auth, read version, read identity
   - records capabilities (v6/v7, wifi package type, etc.)
3. Collector reads devices and schedules polling.

### 5.2 Runtime collection loop (T0: 1-second telemetry)

Every second per device:

1. Collector reads “fast metrics” via API/REST.
2. Collector computes deltas/rates when needed (e.g., traffic bps from byte counters).
3. Collector posts payload to Odoo ingestion endpoint (prefer batching):

```json
{
  "device_uid": "MT-0001",
  "ts": "2026-01-05T10:00:01Z",
  "metrics": {
    "system.cpu.load_pct": 23.5,
    "system.mem.used_bytes": 123456789,
    "iface.ether1.rx_bps": 4312332,
    "iface.ether1.tx_bps": 812331,
    "iface.ether1.rx_packets": 123,
    "iface.ether1.tx_packets": 99
  }
}
```

4. Odoo writes telemetry using bulk SQL (partitioned tables).
5. Odoo updates the latest snapshot table with `UPSERT`.
6. Odoo publishes latest snapshots to bus for active viewers (throttled).

### 5.4 Log and flow ingestion flows (ISP-grade)

Some RouterOS categories are best handled as **streams** rather than polls:

- **Syslog** (recommended): router → syslog receiver → normalization → Odoo/DB
  - Use for: system logs, auth failures, firewall log entries, watchdog events.
- **Traffic-Flow / NetFlow / IPFIX** (recommended for traffic analytics): router → flow collector → storage
  - Use for: top talkers, protocol breakdown, traffic by src/dst/port.

These pipelines must have separate retention policies from 1s telemetry (logs/flows grow differently).

### 5.3 UI live update flow

1. User opens a device “Live” tab.
2. Frontend subscribes to bus channel `mikrotik_monitoring.device.<id>`.
3. When new telemetry arrives:
   - Odoo bus pushes the latest snapshot
   - UI updates KPIs and last-seen timestamp

**Important UX rule you requested:**

- Views show **only latest** values for live widgets; historical browsing is separate.

---

## 6) RouterOS v6/v7 compatibility strategy (reliable, version-safe)

### 6.1 Connection methods

- **Primary (works v6 & v7): RouterOS API** (TCP 8728, or 8729 for TLS)
- **Secondary (v7+): REST API** (if enabled and allowed)

**Rule:** always implement the RouterOS API client path because it offers the broadest compatibility.

Secondary data sources (optional, only when needed):

- SNMP for standard interface counters (when API is restricted)
- Syslog ingestion for logs (when log streaming is required)

ISP-grade rule: treat data sources as a preference order per metric:

1. RouterOS API (preferred)
2. REST API (v7, if enabled)
3. SNMP (for standard counters)
4. Syslog (for event/log stream)

This ensures “reliably” even when some services are disabled on a device.

### 6.2 Capability discovery (feature flags per device)

On first connect and periodically:

- Read `/system/resource/print` → version, uptime, CPU, memory
- Read `/system/package/print` → installed packages (detect wifiwave2 vs legacy wireless)
- Probe availability of key menus (try read, catch “no such command”):
  - WiFi: `/interface/wireless/print` (legacy) vs `/interface/wifi/print` (wifiwave2)
  - IPv6 tables, MPLS, routing tables, containers, LTE

Store results in a `capability` model (per device):

- `routeros_major` (6/7)
- `wifi_mode` (legacy/wifiwave2/none)
- `supports_rest` (bool)
- feature flags (mpls, lte, containers, etc.)

### 6.3 Normalized keys + metric catalog (stability contract)

All collectors must map raw RouterOS fields to stable keys:

- `system.*`
- `iface.<name>.*`
- `routing.bgp.*`
- `routing.ospf.*`
- `dhcp.*`
- `firewall.*`

This isolates UI and storage from RouterOS version differences.

**Add a metric catalog** that defines:

- `key` (string)
- `unit` (e.g., `bytes`, `bps`, `%`, `count`, `celsius`)
- `type` (`gauge`, `counter`)
- `collection_tier` (T0–T3)
- `expected_range` (optional, for validation)

---

## 7) Storage design (optimized for 1s for 90 days)

### 7.1 Storage primitives (separate concerns)

- **Inventory**: slow-changing device metadata
- **Telemetry**: time-series numeric points
- **Events**: state changes (interface down, peer down, login failure)

### 7.2 Telemetry schema (recommended pattern)

To avoid performance issues in PostgreSQL and Odoo, use a **narrow, append-only** telemetry table:

- `device_id`
- `ts_collected` (UTC)
- `metric_key` or `metric_id`
- `value` (numeric)
- `value_text` (nullable, for a small set of textual metrics)

And keep all high-cardinality tables (leases, sessions, tables) out of the 1s telemetry path.

### 7.2.1 ISP-grade storage rule: raw + rollups

To be ISP-grade, time-series storage typically has **two layers**:

- **Raw layer**: 1s points retained for ≥90 days (your requirement).
- **Rollup layer**: aggregated series for long-term reporting (keeps queries fast and storage manageable).

Example rollup policy (adjust to business needs):

- 1s raw: 90 days
- 10s rollup: 180 days
- 1m rollup: 2 years
- 5m rollup: 5 years

Rollups store: min/max/avg/p95 (as needed) and sum for counters.

**Option A (recommended if available): TimescaleDB**

- Create hypertable on `(device_id, ts)`
- Compression and retention policies are easy and efficient

**Option B (pure PostgreSQL): native partitioning**

- Partition telemetry by day (or week) on `ts`
- Use BRIN index on `ts` inside partitions
- Use btree index on `(device_id, ts DESC)` for latest queries

### 7.3 What to store every second

To satisfy “1s for 3 months” without exploding storage:

- Store **selected** high-value telemetry at 1s:
  - system resource (cpu, mem, disk)
  - interface counters (rx/tx bytes, packets, errors) + computed rates
  - connection counts
  - wireless client count / signal summaries
  - LTE signal metrics

For “everything else” from your reference list:

- store as **inventory snapshots** (JSON) on a slower cadence, and/or
- store **events** on change.

### 7.4 Estimating storage (must be validated per deployment)

Storage depends on:

- number of devices
- number of metrics per second
- retention period

Approximate daily points:

$$\text{points/day} = \text{devices} \times \text{metrics_per_device} \times 86400$$

This blueprint requires a sizing step early in implementation.

ISP-grade capacity math to add during implementation:

- **Write rate (points/sec)**:

$$\text{points/sec} = \text{devices} \times \text{metrics_per_device}$$

- **Ingest payload rate** is typically improved by batching (e.g., 1 request contains 1–5 seconds of metrics).
- **DB sizing** must include:
  - index overhead
  - partition count
  - WAL volume
  - replication overhead (if HA)

### 7.4.1 Example sizing (assumption: 3 routers, ~30 interfaces each)

Assumptions (adjust to your environment):

- Routers: 3
- Interfaces per router: 30
- End-users: ~20k (mostly impacts DHCP/PPP/Hotspot table sizes, not T0)
- T0 metric design (store raw counters + key gauges):
  - System gauges per router: ~10 (cpu%, mem used/free, disk free, uptime, temp if available)
  - Interface counters per interface: 4 (rx_bytes_total, tx_bytes_total, rx_packets_total, tx_packets_total)

Approximate T0 points/sec:

- System: $3 \times 10 = 30$ points/sec
- Interfaces: $3 \times 30 \times 4 = 360$ points/sec
- Total: $\approx 390$ points/sec

Approximate points/day:

$$390 \times 86400 \approx 33{,}696{,}000 \text{ points/day}$$

Approximate points for 90 days:

$$33.7\text{M} \times 90 \approx 3.0\text{B points}$$

Storage will depend heavily on schema, indexes, and whether you store `metric_key` as text vs numeric ID.

ISP-grade recommendation:

- Use a **numeric metric_id** (catalog table) to reduce row size.
- Keep indexes minimal on raw tables; rely on partitions + BRIN for time ranges.
- Keep “latest snapshot” as the primary UI read path.

### 7.4.2 Dynamic T0 interface selection (no fixed list)

To avoid hardcoding “critical interfaces”, select them dynamically from real router data:

- Always include detected uplinks (default route interface, PPPoE server interfaces, VRRP master).
- Include top-N interfaces by traffic over last 5 minutes (e.g., N=5 or N=10 per router).
- Include any interfaces tagged as SLA/business-critical.

ISP-grade guardrails (to avoid performance issues):

- Cap T0 interfaces per router (e.g., max 10) and demote the rest to T1/T2.
- Cap T0 metrics per router (budget) so adding new interfaces doesn’t explode ingestion.

### 7.5 Latest snapshot table (fast UI, low DB load)

- Latest per device: `(device_id, metric_key)` most recent sample
- Keep a **latest snapshot table** updated on ingestion to avoid expensive queries:
  - `mikrotik_metric_latest(device_id, metric_key, ts, value_*)`

This gives fast UI reads while raw telemetry remains append-only.

### 7.6 Partitioning and retention (pure PostgreSQL)

- Partition telemetry by day on `ts_collected`.
- Keep 90+ daily partitions.
- Drop partitions older than retention (fast, constant-time retention).
- Index strategy:

  - `(device_id, ts_collected DESC)` btree for latest per device
  - BRIN on `ts_collected` per partition for range scans

  ISP-grade notes:

  - Use separate tablespaces/disks if possible (WAL vs data).
  - Consider compression (Timescale) or columnar extensions only if supported operationally.

---

## 8) Data correctness (traffic and counters)

Traffic “real-time” must be computed correctly:

- Store raw counters: `rx_bytes_total`, `tx_bytes_total`, `rx_packets_total`, `tx_packets_total`.
- Compute rates as:

$$\text{bps} = \frac{(\Delta\text{bytes}) \times 8}{\Delta t}$$

Correctness rules:

- Detect router reboot (uptime decreased) → reset rate baseline.
- Handle counter wrap/rollover (treat negative delta as reset).
- Use monotonic timestamps from collector; always store `ts_received` too.
- Validate units (never mix bps/Bps).

ISP-grade additional correctness:

- Maintain per-device poll latency; if latency spikes, mark derived rates as lower confidence.
- For interface rates, always compute from byte counters; do not depend on optional “current rate” fields.
- Keep last counter state in collector memory (or durable cache) to compute deltas without DB reads.

---

## 9) Professional Odoo UX (standard, clean)

### 9.1 Views (backend)

1. **Devices**

- List view: name, host, version, last_seen, status
- Form view:
  - General (host, creds, groups)
  - Capabilities (read-only)
  - Live (KPIs + last update)
  - Interfaces (latest RX/TX per interface)

2. **Telemetry (read-only)**

- List view for historical points (admin/debug)
- Default filters: device + last 15 minutes

**No extra pages are required beyond these standard views.**

### 9.2 Real-time rendering approach

- Use Odoo bus to push latest snapshots
- The Live tab should update without page reload
- On disconnect, show “Last update: …” and stale indicator

ISP-grade UX notes:

- Provide a clear status model: **Up / Degraded / Down / Unknown** per device.
- Keep UI lightweight; historical graphs should read from rollups by default.

---

## 10) Security and safety (minimum required)

- Credentials must be stored securely:
  - Use Odoo’s password storage mechanisms (encrypted fields if available)
  - Restrict access via groups (Network Monitoring Admin / Viewer)
- Ingestion endpoint must be authenticated:
  - HMAC signature or Odoo API key token per collector
- Rate limit ingestion to prevent abuse

Operational security (recommended):

- Collector network is private (VPN/VLAN) to reach routers.
- Use TLS for Odoo endpoints.
- Per-collector token rotation and audit logging.

ISP-grade security additions:

- Secrets management (Vault/KMS) for router credentials and collector tokens.
- Strong tenant isolation and audit logs for data access.
- Network controls: collectors in secured subnets; strict egress; allow-list router access.
- Compliance: define retention policies separately for metrics vs logs vs flows.

---

## 11) Operational excellence (avoid performance issues in production)

### 11.1 Observability

- Collector metrics: per-device latency, error rate, queue depth, dropped polls.
- Odoo metrics: ingestion latency, DB write time, bus publish time.

### 11.2 Scaling model

- Scale by adding more collector instances (horizontal).
- Shard devices across collectors (static assignment or via coordinator).

### 11.4 Deployment topologies (ISP-grade)

- **Small ISP / single region**: 1–3 collectors (sharded), 1 DB primary + replica, optional log/flow collectors.
- **Multi-region ISP**: collectors per region + regional buffering; central DB or per-region DB with federation.

### 11.5 Change management

- Schema migrations designed for large tables (partition-aware).
- Safe rollout strategy for collector changes (canary per region).
- Versioned metric catalog (backward compatible keys).

### 11.6 Runbooks

- Router unreachable spikes
- Collector queue growth
- DB partition/retention failure
- Time drift detection
- High CPU on RouterOS devices due to polling

### 11.3 Failure handling

- Circuit breaker per device (avoid hammering a failing router).
- Exponential backoff with max cap.
- Local buffering when Odoo/DB is down.

---

## 12) Implementation Plan (phased)

### Phase 1 — Core device & ingestion

- Device model + capability discovery
- Collector MVP for 1s fast metrics
- Telemetry storage (partitioning)
- Latest snapshot table
- Device list + form + Live tab

### Phase 2 — Interfaces + traffic correctness

- Per-interface counters and rate calculation standardization
- Consistent naming and units (bps, bytes, packets)
- Validation against RouterOS CLI outputs

### Phase 3 — Expand coverage of categories

- DHCP, DNS, hotspot/PPP, VPN, routing neighbors
- Firewall counters and connection tracking counts
- Wireless/LTE expansions based on capabilities

### Phase 4 — Retention and operations

- Automated partition creation/drop
- Monitoring of collector health
- Backpressure / buffering when Odoo is down

### Phase 5 — ISP-grade operations

- Rollups/downsampling implementation
- Multi-tenancy hardening + audit
- NOC alerting workflows + flapping control
- HA/DR drills and load testing at target scale

---

## 13) TODO Checklist (to make it production-ready)

### 13.1 Odoo module structure

- [ ] Add `security/ir.model.access.csv` and security groups
- [ ] Add models:
  - [ ] `mikrotik.device`
  - [ ] `mikrotik.device.capability`
  - [ ] `mikrotik.metric.point` (partitioned)
  - [ ] `mikrotik.metric.latest`
  - [ ] `mikrotik.event` (state changes)
- [ ] Add server actions:
  - [ ] Test connection
  - [ ] Refresh capabilities

### 13.2 Database & retention

- [ ] Choose Option A (TimescaleDB) or Option B (native partitions)
- [ ] Implement partition management job
- [ ] Enforce retention ≥ 90 days for 1s telemetry
- [ ] Add indexes for latest queries and time-range queries
- [ ] Add rollups/downsampling tables and policies
- [ ] Validate WAL/replication impact under target scale

### 13.3 Collector service

- [ ] Implement RouterOS API client layer (v6/v7)
- [ ] Implement capability probe + command map
- [ ] Implement 1s polling loop (asyncio or threaded)
- [ ] Compute rates from counters correctly (handle wrap/reset)
- [ ] Post to Odoo ingestion endpoint with retries
- [ ] Add sharding strategy + bounded concurrency
- [ ] Add local durable buffer (disk queue) and replay
- [ ] Add syslog + flow collectors (if required)

### 13.4 Realtime UI

- [ ] Publish latest snapshot on bus per device
- [ ] Live tab subscribes and updates KPIs
- [ ] Show last_seen and stale state

### 13.5 Data correctness

- [ ] Define metric units and conversions (bytes→bps)
- [ ] Validate sampled data against RouterOS values
- [ ] Handle missing features gracefully (feature flags)

### 13.6 Testing & QA

- [ ] Unit tests for rate calculation (counter reset/wrap)
- [ ] Integration test with a RouterOS lab device (v6 and v7)
- [ ] Load test: N devices × M metrics × 1s
- [ ] HA test: kill collector nodes, verify recovery and replay
- [ ] Data quality tests: reboot/reset/wrap scenarios at scale

---

## 14) Open decisions you must confirm early

1. Expected device count and average interface count (sizing).
2. Whether TimescaleDB is allowed; if not, use native partitions.
3. Which “T0 metric set” is mandatory at 1s (to cap storage growth).
4. Required retention beyond 90 days (rollup horizons).
5. Tenant model: per-customer vs per-region vs single-tenant.

---

## 15) Definition of Done (what “perfect” means here)

- Real-time view updates smoothly and shows only latest values.
- 1-second telemetry is stored and queryable for ≥3 months.
- Works with RouterOS v6 and v7 via capability detection.
- UI is standard Odoo-professional: readable KPIs, clear status, no clutter.
- Collector is reliable: retries, logging, health monitoring.
- Data is correct: rate calculations validated, fallbacks for missing features.

ISP-grade done criteria:

- Defined SLOs for freshness/availability and measured in production.
- Scales to target device count without DB/Odoo degradation.
- Rollups make long-range queries fast and predictable.
- Alerting works with flapping control and maintenance windows.
- Runbooks exist and have been exercised (failure drills).
