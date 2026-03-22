<template>
  <div>
    <div class="page-header">
      <div>
        <h2>장비 관제</h2>
        <p class="breadcrumb" v-if="props.selectedBuildingId || props.selectedSiteId">{{ filterLabel }}</p>
      </div>
      <div class="header-actions">
        <input v-model="search" class="search" placeholder="장비명/IP 검색..." />
        <select v-model="statusFilter" class="filter-select">
          <option value="">전체 상태</option>
          <option value="MANAGED">MANAGED</option>
          <option value="PENDING">PENDING</option>
          <option value="ERROR">ERROR</option>
        </select>
        <button class="btn-refresh" @click="loadDevices" title="새로고침">↻</button>
      </div>
    </div>

    <div v-if="loading" class="loading">장비 목록을 불러오는 중...</div>

    <table v-else class="device-table">
      <thead>
        <tr>
          <th>장비명</th>
          <th>IP 주소</th>
          <th>프로토콜</th>
          <th>상태</th>
          <th>모델</th>
          <th>업타임</th>
          <th>마지막 폴링</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filteredDevices.length === 0">
          <td colspan="7" class="empty-row">등록된 장비가 없습니다.</td>
        </tr>
        <tr
          v-for="device in filteredDevices"
          :key="device.id"
          class="device-row"
          :class="{ selected: selectedDevice?.id === device.id }"
          @click="openMonitor(device)"
        >
          <td><strong>{{ device.name }}</strong></td>
          <td class="mono">{{ device.ip_addr }}</td>
          <td><span class="proto-badge">{{ device.protocol }}</span></td>
          <td><StatusBadge :status="device.status" /></td>
          <td>{{ device.model || "—" }}</td>
          <td class="txt-muted small">{{ parseUptime(device.uptime) }}</td>
          <td class="txt-muted small">{{ device.last_polled_at ? formatTime(device.last_polled_at) : "—" }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 관제 슬라이더 -->
    <DrawerPanel
      v-model="drawerOpen"
      :title="selectedDevice ? selectedDevice.name : '관제'"
      :width="640"
    >
      <div v-if="selectedDevice" class="monitor-content">

        <!-- 탭 -->
        <div v-if="selectedDevice.status === 'MANAGED'" class="tabs-wrap">
          <div class="tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="tab"
              :class="{ active: activeTab === tab.key }"
              @click="switchTab(tab.key)"
            >{{ tab.label }}</button>
          </div>

          <div class="tab-body">

            <!-- ── 기본정보 탭 ── -->
            <div v-if="activeTab === 'info'" class="info-tab">

              <!-- 장비 요약 -->
              <div class="device-summary">
                <StatusBadge :status="selectedDevice.status" />
                <span class="summary-name">{{ selectedDevice.name }}</span>
              </div>

              <!-- 필드 목록 -->
              <div class="field-list">
                <div class="field-item">
                  <span class="field-lbl">MAC</span>
                  <span class="field-sep">:</span>
                  <span class="field-val mono-val">{{ selectedDevice.mac_addr || "—" }}</span>
                </div>
                <div class="field-item">
                  <span class="field-lbl">IP</span>
                  <span class="field-sep">:</span>
                  <span class="field-val mono-val">{{ selectedDevice.ip_addr }}</span>
                </div>
                <div class="field-item">
                  <span class="field-lbl">모델</span>
                  <span class="field-sep">:</span>
                  <span class="field-val">{{ selectedDevice.model || "—" }}</span>
                </div>
                <div class="field-item">
                  <span class="field-lbl">시리얼</span>
                  <span class="field-sep">:</span>
                  <span class="field-val mono-val">{{ selectedDevice.serial_no || "—" }}</span>
                </div>
                <div class="field-item">
                  <span class="field-lbl">SW 버전</span>
                  <span class="field-sep">:</span>
                  <span class="field-val">{{ selectedDevice.sw_version || "—" }}</span>
                </div>
                <div class="field-item">
                  <span class="field-lbl">업타임</span>
                  <span class="field-sep">:</span>
                  <span class="field-val uptime-val">{{ parseUptime(selectedDevice.uptime) }}</span>
                </div>
              </div>

              <!-- 포트 현황 (접기/펴기) -->
              <div class="section-block">
                <div class="section-header" @click="portExpanded = !portExpanded">
                  <div class="section-title-row">
                    <span class="section-chevron">{{ portExpanded ? '▾' : '▸' }}</span>
                    <span class="section-title">포트 현황</span>
                    <span v-if="ports.length" class="section-count">{{ ports.length }}개</span>
                  </div>
                  <div class="section-actions" @click.stop>
                    <button class="action-btn" @click="pollAndReload" :disabled="polling" title="장비 재요청">
                      <span :class="{ spinning: polling }">⟳</span>
                      <span class="btn-label">{{ polling ? "요청 중" : "재요청" }}</span>
                    </button>
                    <button class="action-btn" @click="reloadPorts" :disabled="loadingPorts" title="DB 새로고침">
                      <span :class="{ spinning: loadingPorts }">↻</span>
                      <span class="btn-label">새로고침</span>
                    </button>
                  </div>
                </div>
                <div v-show="portExpanded">
                  <div v-if="loadingPorts" class="tab-loading">포트 정보 불러오는 중...</div>
                  <SwitchPortMap v-else :ports="ports" :label="selectedDevice.name" compact />
                </div>
              </div>

              <!-- VLAN 맵 (접기/펴기) -->
              <div class="section-block">
                <div class="section-header" @click="vlanExpanded = !vlanExpanded">
                  <div class="section-title-row">
                    <span class="section-chevron">{{ vlanExpanded ? '▾' : '▸' }}</span>
                    <span class="section-title">VLAN 맵</span>
                    <span v-if="vlans.length" class="section-count">{{ vlans.length }}개</span>
                  </div>
                  <div class="section-actions" @click.stop>
                    <button class="action-btn" @click="reloadVlans" :disabled="loadingVlans" title="새로고침">
                      <span :class="{ spinning: loadingVlans }">↻</span>
                      <span class="btn-label">새로고침</span>
                    </button>
                  </div>
                </div>
                <div v-show="vlanExpanded">
                  <div v-if="loadingVlans" class="tab-loading">VLAN 정보 불러오는 중...</div>
                  <VlanMap v-else :vlans="vlans" :ports="ports" />
                </div>
              </div>
            </div>

            <!-- ── 단말 탭 ── -->
            <div v-if="activeTab === 'endpoints'">
              <div class="section-header-flat">
                <span class="section-title">단말 목록</span>
                <button class="action-btn" @click="reloadEndpoints" :disabled="loadingEndpoints">
                  <span :class="{ spinning: loadingEndpoints }">↻</span>
                  <span class="btn-label">새로고침</span>
                </button>
              </div>
              <div v-if="loadingEndpoints" class="tab-loading">단말 정보 불러오는 중...</div>
              <table v-else class="data-table">
                <thead><tr><th>MAC</th><th>IP</th><th>포트</th><th>VLAN</th></tr></thead>
                <tbody>
                  <tr v-if="endpoints.length === 0"><td colspan="4" class="empty">단말 정보 없음</td></tr>
                  <tr v-for="e in endpoints" :key="e.id">
                    <td class="mono">{{ e.mac_addr }}</td>
                    <td>{{ e.ip_addr || "—" }}</td>
                    <td class="mono">{{ e.port_name || "—" }}</td>
                    <td>{{ e.vlan_id || "—" }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- ── 알람 탭 ── -->
            <div v-if="activeTab === 'alarms'">
              <table class="data-table">
                <thead><tr><th>유형</th><th>심각도</th><th>메시지</th><th>상태</th><th>발생</th></tr></thead>
                <tbody>
                  <tr v-if="deviceAlarms.length === 0"><td colspan="5" class="empty">알람 이력 없음</td></tr>
                  <tr v-for="a in deviceAlarms" :key="a.id">
                    <td>{{ a.alarm_type }}</td>
                    <td><span :class="'sev-' + a.severity.toLowerCase()">{{ a.severity }}</span></td>
                    <td>{{ a.message }}</td>
                    <td>{{ a.status }}</td>
                    <td class="txt-muted">{{ formatTime(a.created_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- ── Running Config 탭 ── -->
            <div v-if="activeTab === 'config'" class="config-tab">
              <div class="section-header-flat">
                <span class="section-title">Running Config</span>
                <button class="action-btn action-btn-primary" @click="fetchRunningConfig" :disabled="loadingConfig">
                  <span :class="{ spinning: loadingConfig }">⟳</span>
                  <span class="btn-label">{{ loadingConfig ? "가져오는 중..." : "장비에서 가져오기" }}</span>
                </button>
              </div>
              <div v-if="configError" class="config-error">{{ configError }}</div>
              <div v-if="!runningConfig && !loadingConfig && !configError" class="config-empty">
                버튼을 눌러 Running Config를 장비에서 가져오세요.
              </div>
              <pre v-if="runningConfig" class="config-viewer">{{ runningConfig }}</pre>
            </div>

          </div>
        </div>

        <div v-else class="pending-notice">
          <p v-if="selectedDevice.status === 'PENDING'">⏳ 장비 정보 수집 중입니다.</p>
          <p v-else>❌ 장비 연결에 실패했습니다. 연결 정보를 확인하세요.</p>
        </div>
      </div>
    </DrawerPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useDeviceStore } from "@/stores/device";
import { useTopologyStore } from "@/stores/topology";
import { useAlarmStore } from "@/stores/alarm";
import StatusBadge from "@/components/StatusBadge.vue";
import DrawerPanel from "@/components/DrawerPanel.vue";
import SwitchPortMap from "@/components/SwitchPortMap.vue";
import VlanMap from "@/components/VlanMap.vue";
import api from "@/api/client";

const props = defineProps<{ selectedSiteId?: number; selectedBuildingId?: number }>();

const deviceStore = useDeviceStore();
const topologyStore = useTopologyStore();
const alarmStore = useAlarmStore();

const search = ref("");
const statusFilter = ref("");
const loading = computed(() => deviceStore.loading);

const drawerOpen = ref(false);
const selectedDevice = ref<any>(null);
const activeTab = ref("info");

const ports = ref<any[]>([]);
const vlans = ref<any[]>([]);
const endpoints = ref<any[]>([]);
const runningConfig = ref("");
const configError = ref("");

const loadingPorts = ref(false);
const loadingVlans = ref(false);
const loadingEndpoints = ref(false);
const loadingConfig = ref(false);
const polling = ref(false);

const portExpanded = ref(true);
const vlanExpanded = ref(true);
const monitorGeneration = ref(0);

const tabs = [
  { key: "info", label: "기본정보" },
  { key: "endpoints", label: "단말" },
  { key: "alarms", label: "알람" },
  { key: "config", label: "Running Config" },
];

const deviceAlarms = computed(() =>
  alarmStore.alarms.filter((a) => a.device_id === selectedDevice.value?.id)
);

// ── Uptime parser ──────────────────────────────────────────────────
function parseUptime(raw: string | null | undefined): string {
  if (!raw) return "—";
  let total = 0; // total minutes

  const wm = raw.match(/(\d+)\s*w(?:eek)?s?/i);
  if (wm) total += parseInt(wm[1]) * 7 * 24 * 60;

  const dm = raw.match(/(\d+)\s*d(?:ay)?s?/i);
  if (dm) total += parseInt(dm[1]) * 24 * 60;

  // "HH:MM:SS" time part (Python timedelta format)
  const timePart = raw.match(/(\d+):(\d{2}):\d{2}/);
  if (timePart) {
    total += parseInt(timePart[1]) * 60 + parseInt(timePart[2]);
  } else {
    const hm = raw.match(/(\d+)\s*h(?:our)?s?/i);
    if (hm) total += parseInt(hm[1]) * 60;
    const mm = raw.match(/(\d+)\s*m(?:in(?:ute)?)?s?(?!\s*(?:onth|ac))/i);
    if (mm) total += parseInt(mm[1]);
  }

  if (total === 0 && !/\d/.test(raw)) return raw;

  const w = Math.floor(total / (7 * 24 * 60)); total %= 7 * 24 * 60;
  const d = Math.floor(total / (24 * 60)); total %= 24 * 60;
  const h = Math.floor(total / 60);
  const m = total % 60;

  const parts: string[] = [];
  if (w) parts.push(`${w}w`);
  if (d) parts.push(`${d}d`);
  if (h) parts.push(`${h}h`);
  if (m || parts.length === 0) parts.push(`${m}m`);
  return parts.join(" ");
}

// ── Data loaders ───────────────────────────────────────────────────
async function loadPorts() {
  const id = selectedDevice.value?.id;
  if (!id) return;
  const gen = monitorGeneration.value;
  loadingPorts.value = true;
  try {
    const data = (await api.get(`/devices/${id}/ports`)).data;
    if (monitorGeneration.value === gen) ports.value = data;
  } finally {
    if (monitorGeneration.value === gen) loadingPorts.value = false;
  }
}

async function loadVlans() {
  const id = selectedDevice.value?.id;
  if (!id) return;
  const gen = monitorGeneration.value;
  loadingVlans.value = true;
  try {
    const data = (await api.get(`/devices/${id}/vlans`)).data;
    if (monitorGeneration.value === gen) vlans.value = data;
  } finally {
    if (monitorGeneration.value === gen) loadingVlans.value = false;
  }
}

async function loadEndpoints() {
  const id = selectedDevice.value?.id;
  if (!id) return;
  loadingEndpoints.value = true;
  try { endpoints.value = (await api.get(`/devices/${id}/endpoints`)).data; }
  finally { loadingEndpoints.value = false; }
}

async function reloadPorts() { ports.value = []; await loadPorts(); }
async function reloadVlans() { vlans.value = []; await loadVlans(); }
async function reloadEndpoints() { endpoints.value = []; await loadEndpoints(); }

async function pollAndReload() {
  const id = selectedDevice.value?.id;
  if (!id) return;
  polling.value = true;
  try {
    await api.post(`/devices/${id}/poll`);
    // Wait for Celery task to complete, then reload
    await new Promise((r) => setTimeout(r, 5000));
    await Promise.all([loadPorts(), loadVlans()]);
  } finally {
    polling.value = false;
  }
}

async function fetchRunningConfig() {
  const id = selectedDevice.value?.id;
  if (!id) return;
  loadingConfig.value = true;
  configError.value = "";
  try {
    const res = await api.post(`/devices/${id}/running-config`);
    runningConfig.value = res.data.config;
  } catch (e: any) {
    configError.value = e?.response?.data?.detail || "Running Config 가져오기 실패";
  } finally {
    loadingConfig.value = false;
  }
}

async function openMonitor(device: any) {
  monitorGeneration.value++;
  selectedDevice.value = device;
  drawerOpen.value = true;
  activeTab.value = "info";
  ports.value = [];
  vlans.value = [];
  endpoints.value = [];
  runningConfig.value = "";
  configError.value = "";
  loadingConfig.value = false;
  portExpanded.value = true;
  vlanExpanded.value = true;

  if (device.status === "MANAGED") {
    loadPorts();
    loadVlans();
  }
}

async function switchTab(tab: string) {
  activeTab.value = tab;
  const id = selectedDevice.value?.id;
  if (!id) return;
  if (tab === "endpoints" && endpoints.value.length === 0) await loadEndpoints();
  else if (tab === "alarms") alarmStore.fetchAlarms();
}

const filteredDevices = computed(() => {
  const q = search.value.toLowerCase();
  let list = deviceStore.devices;
  if (statusFilter.value) list = list.filter((d) => d.status === statusFilter.value);
  if (q) list = list.filter((d) => d.name.toLowerCase().includes(q) || d.ip_addr.includes(q));
  return list;
});

const filterLabel = computed(() => {
  if (props.selectedBuildingId) {
    for (const g of topologyStore.groups) {
      for (const s of g.sites) {
        const b = s.buildings.find((b) => b.id === props.selectedBuildingId);
        if (b) return `${g.name} > ${s.name} > ${b.name}`;
      }
    }
  }
  if (props.selectedSiteId) {
    for (const g of topologyStore.groups) {
      const s = g.sites.find((s) => s.id === props.selectedSiteId);
      if (s) return `${g.name} > ${s.name}`;
    }
  }
  return "";
});

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function loadDevices() {
  deviceStore.fetchDevices({ site_id: props.selectedSiteId, building_id: props.selectedBuildingId });
}

watch([() => props.selectedSiteId, () => props.selectedBuildingId], loadDevices);
onMounted(() => { loadDevices(); alarmStore.fetchAlarms(); });
</script>

<style scoped>
/* ── Page layout ── */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
h2 { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.05em; }
.breadcrumb { color: var(--text-muted); font-size: 0.85rem; margin-top: 0.2rem; }
.header-actions { display: flex; gap: 0.5rem; align-items: center; }
.search {
  padding: 0.4rem 0.7rem; border: 1px solid var(--border-input); border-radius: 2px;
  font-size: 0.87rem; width: 180px; outline: revert;
  color: var(--text-primary); background: var(--bg-input);
}
.search:focus { border-color: var(--accent-primary); outline: none; }
.search::placeholder { color: var(--text-muted); }
.filter-select {
  padding: 0.4rem 0.7rem; border: 1px solid var(--border-input); border-radius: 2px;
  font-size: 0.87rem; background: var(--bg-input); color: var(--text-primary);
}
.btn-refresh {
  padding: 0.4rem 0.65rem; background: var(--bg-elevated); border: 1px solid var(--border-input);
  border-radius: 2px; cursor: pointer; font-size: 1rem; color: var(--text-secondary); transition: all 0.15s;
}
.btn-refresh:hover { color: var(--text-primary); background: var(--bg-surface); }

/* ── Device table ── */
.device-table { width: 100%; border-collapse: collapse; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 3px; }
thead { background: var(--bg-table-header); }
th { padding: 0.6rem 1rem; text-align: left; font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid var(--border-subtle); }
td { padding: 0.7rem 1rem; border-top: 1px solid var(--border-color); font-size: 0.88rem; color: var(--text-primary); }
.device-row { cursor: pointer; transition: background 0.1s; }
.device-row:hover td { background: var(--bg-table-hover); }
.device-row.selected td { background: var(--accent-active-bg); border-left: 2px solid var(--accent-primary); }
.empty-row { text-align: center; color: var(--text-muted); padding: 2.5rem 1rem !important; }
.mono { font-family: 'Consolas', 'Monaco', monospace; font-size: 0.85rem; color: var(--text-secondary); }
.small { font-size: 0.85rem; }
.txt-muted { color: var(--text-muted); }
.proto-badge { background: var(--accent-active-bg); color: var(--accent-hover); padding: 0.15rem 0.5rem; border-radius: 2px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; }
.loading { text-align: center; padding: 3rem; color: var(--text-muted); }

/* ── Monitor drawer ── */
.monitor-content { display: flex; flex-direction: column; }

/* ── Device summary ── */
.device-summary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--border-color);
}
.summary-name {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-muted);
}

/* ── Field list ── */
.field-list {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}
.field-item {
  display: flex;
  align-items: baseline;
  gap: 0.3rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--border-color);
}
.field-item:last-child { border-bottom: none; }
.field-lbl {
  font-size: 0.78rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  min-width: 60px;
  flex-shrink: 0;
}
.field-sep {
  font-size: 0.78rem;
  color: var(--text-muted);
  flex-shrink: 0;
}
.field-val {
  font-size: 0.88rem;
  color: var(--text-primary);
  font-weight: 500;
  word-break: break-all;
}
.mono-val { font-family: monospace; font-size: 0.88rem; }
.uptime-val { font-family: monospace; color: var(--accent-hover); font-weight: 600; }

/* ── Tabs ── */
.tabs-wrap { display: flex; flex-direction: column; }
.tabs { display: flex; border-bottom: 2px solid var(--border-subtle); flex-shrink: 0; }
.tab {
  padding: 0.65rem 1.1rem; background: none; border: none; cursor: pointer;
  font-size: 0.93rem; color: var(--text-muted);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: all 0.15s; white-space: nowrap;
}
.tab:hover { color: var(--text-primary); }
.tab.active { color: var(--accent-primary); border-bottom-color: var(--accent-primary); font-weight: 600; }

.tab-body { padding-top: 1rem; }
.tab-loading { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.95rem; }

/* ── Section block (collapsible) ── */
.section-block {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  margin-bottom: 0.9rem;
  /* overflow: hidden 제거 — 포트 툴팁이 클리핑됨 */
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 0.9rem;
  background: var(--bg-elevated);
  cursor: pointer;
  user-select: none;
  transition: background 0.12s;
  border-radius: 8px 8px 0 0;
}
.section-header:hover { background: var(--bg-surface); }

.section-header-flat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.section-chevron {
  font-size: 0.9rem;
  color: var(--text-muted);
  width: 14px;
}
.section-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.section-count {
  font-size: 0.78rem;
  color: var(--text-muted);
  background: var(--bg-base);
  padding: 0.1rem 0.45rem;
  border-radius: 20px;
  border: 1px solid var(--border-color);
}
.section-actions {
  display: flex;
  gap: 0.4rem;
}

/* ── Action buttons ── */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  background: var(--bg-base);
  border: 1px solid var(--border-input);
  border-radius: 5px;
  color: var(--text-secondary);
  font-size: 0.88rem;
  cursor: pointer;
  transition: all 0.13s;
  white-space: nowrap;
}
.action-btn:hover:not(:disabled) {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--text-muted);
}
.action-btn:disabled { opacity: 0.5; cursor: default; }
.action-btn-primary {
  background: var(--accent-active-bg);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  font-weight: 600;
}
.action-btn-primary:hover:not(:disabled) {
  background: var(--accent-primary);
  color: #fff;
}
.btn-label { font-size: 0.88rem; }

/* Section body padding */
.section-block > div:last-child { padding: 0.75rem; }

/* ── Running config ── */
.config-tab { display: flex; flex-direction: column; gap: 0.75rem; }
.config-viewer {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 0.9rem 1rem;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.88rem;
  color: var(--text-secondary);
  overflow: auto;
  max-height: 520px;
  white-space: pre;
  line-height: 1.6;
}
.config-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.95rem;
  padding: 2.5rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}
.config-error {
  color: var(--danger);
  font-size: 0.9rem;
  padding: 0.6rem 0.9rem;
  background: var(--danger-bg);
  border-radius: 6px;
}

/* ── Data table ── */
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 0.55rem 0.7rem; text-align: left; font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border-subtle); }
.data-table td { padding: 0.65rem 0.7rem; font-size: 0.93rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }
.empty { text-align: center; color: var(--text-muted); padding: 2.5rem !important; }

.sev-critical { color: var(--danger); font-weight: 700; }
.sev-warning { color: var(--warning); font-weight: 600; }
.sev-info { color: var(--accent-primary); }

.pending-notice {
  background: var(--bg-elevated); border: 1px solid var(--border-subtle);
  border-radius: 8px; padding: 1.5rem; text-align: center; color: var(--text-secondary); font-size: 0.95rem;
}

/* ── Animations ── */
@keyframes spin { to { transform: rotate(360deg); } }
.spinning { display: inline-block; animation: spin 0.8s linear infinite; }
</style>
