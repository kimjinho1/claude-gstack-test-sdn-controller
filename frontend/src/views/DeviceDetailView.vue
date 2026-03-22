<template>
  <div v-if="device">
    <!-- Device Header -->
    <div class="device-header">
      <div>
        <h2>{{ device.name }}</h2>
        <span class="ip">{{ device.ip_addr }}</span>
        <span class="sep">·</span>
        <span class="mac">{{ device.mac_addr }}</span>
      </div>
      <StatusBadge :status="device.status" />
    </div>

    <!-- Device Info Cards -->
    <div class="info-grid">
      <div class="info-card">
        <div class="info-label">모델</div>
        <div class="info-value">{{ device.model || "—" }}</div>
      </div>
      <div class="info-card">
        <div class="info-label">시리얼</div>
        <div class="info-value mono">{{ device.serial_no || "—" }}</div>
      </div>
      <div class="info-card">
        <div class="info-label">소프트웨어 버전</div>
        <div class="info-value">{{ device.sw_version || "—" }}</div>
      </div>
      <div class="info-card">
        <div class="info-label">업타임</div>
        <div class="info-value">{{ device.uptime || "—" }}</div>
      </div>
    </div>

    <!-- Tabs (only for MANAGED) -->
    <div v-if="device.status === 'MANAGED'" class="tabs-container">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >{{ tab.label }}</button>
      </div>

      <div class="tab-content">
        <!-- Ports -->
        <div v-if="activeTab === 'ports'">
          <table class="data-table">
            <thead><tr><th>포트</th><th>상태</th><th>속도</th><th>VLAN</th><th>연결 MAC</th><th>연결 IP</th></tr></thead>
            <tbody>
              <tr v-if="ports.length === 0"><td colspan="6" class="empty">포트 정보 없음</td></tr>
              <tr v-for="p in ports" :key="p.id">
                <td class="mono">{{ p.port_name }}</td>
                <td><span :class="p.port_status === 'UP' ? 'up' : 'down'">{{ p.port_status }}</span></td>
                <td>{{ p.speed || "—" }}</td>
                <td>{{ p.vlan_id || "—" }}</td>
                <td class="mono">{{ p.connected_mac || "—" }}</td>
                <td>{{ p.connected_ip || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- VLANs -->
        <div v-if="activeTab === 'vlans'">
          <table class="data-table">
            <thead><tr><th>VLAN ID</th><th>이름</th><th>수집 시각</th></tr></thead>
            <tbody>
              <tr v-if="vlans.length === 0"><td colspan="3" class="empty">VLAN 정보 없음</td></tr>
              <tr v-for="v in vlans" :key="v.id">
                <td class="mono">{{ v.vlan_id }}</td>
                <td>{{ v.vlan_name || "—" }}</td>
                <td>{{ formatTime(v.polled_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Endpoints -->
        <div v-if="activeTab === 'endpoints'">
          <table class="data-table">
            <thead><tr><th>MAC</th><th>IP</th><th>포트</th><th>VLAN</th><th>수집 시각</th></tr></thead>
            <tbody>
              <tr v-if="endpoints.length === 0"><td colspan="5" class="empty">단말 정보 없음</td></tr>
              <tr v-for="e in endpoints" :key="e.id">
                <td class="mono">{{ e.mac_addr }}</td>
                <td>{{ e.ip_addr || "—" }}</td>
                <td class="mono">{{ e.port_name || "—" }}</td>
                <td>{{ e.vlan_id || "—" }}</td>
                <td>{{ formatTime(e.polled_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Alarms -->
        <div v-if="activeTab === 'alarms'">
          <table class="data-table">
            <thead><tr><th>유형</th><th>심각도</th><th>메시지</th><th>상태</th><th>발생 시각</th></tr></thead>
            <tbody>
              <tr v-if="deviceAlarms.length === 0"><td colspan="5" class="empty">알람 이력 없음</td></tr>
              <tr v-for="a in deviceAlarms" :key="a.id">
                <td>{{ a.alarm_type }}</td>
                <td><span :class="a.severity.toLowerCase()">{{ a.severity }}</span></td>
                <td>{{ a.message }}</td>
                <td>{{ a.status }}</td>
                <td>{{ formatTime(a.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else class="pending-notice">
      <p>{{ device.status === 'PENDING' ? '⏳ 장비 정보 수집 중입니다. 잠시 후 새로고침 해주세요.' : '❌ 장비 연결에 실패했습니다. 연결 정보를 확인해주세요.' }}</p>
    </div>
  </div>

  <div v-else class="loading">장비 정보를 불러오는 중...</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import api from "@/api/client";
import { useAlarmStore } from "@/stores/alarm";
import StatusBadge from "@/components/StatusBadge.vue";

const route = useRoute();
const alarmStore = useAlarmStore();

const device = ref<any>(null);
const ports = ref<any[]>([]);
const vlans = ref<any[]>([]);
const endpoints = ref<any[]>([]);
const activeTab = ref("ports");

const tabs = [
  { key: "ports", label: "포트 현황" },
  { key: "vlans", label: "VLAN 맵" },
  { key: "endpoints", label: "단말 목록" },
  { key: "alarms", label: "알람 이력" },
];

const deviceAlarms = computed(() =>
  alarmStore.alarms.filter((a) => a.device_id === device.value?.id)
);

function formatTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function switchTab(tab: string) {
  activeTab.value = tab;
  await loadTabData(tab);
}

async function loadTabData(tab: string) {
  const id = route.params.id;
  if (tab === "ports") ports.value = (await api.get(`/devices/${id}/ports`)).data;
  else if (tab === "vlans") vlans.value = (await api.get(`/devices/${id}/vlans`)).data;
  else if (tab === "endpoints") endpoints.value = (await api.get(`/devices/${id}/endpoints`)).data;
  else if (tab === "alarms") alarmStore.fetchAlarms();
}

onMounted(async () => {
  const id = route.params.id;
  device.value = (await api.get(`/devices/${id}`)).data;
  if (device.value.status === "MANAGED") {
    await loadTabData("ports");
  }
});
</script>

<style scoped>
.device-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
h2 { font-size: 1.4rem; font-weight: 700; }
.ip, .mac { font-size: 0.9rem; color: #718096; }
.sep { color: #cbd5e0; margin: 0 0.3rem; }
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
.info-card { background: white; border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.info-label { font-size: 0.78rem; color: #718096; margin-bottom: 0.3rem; }
.info-value { font-size: 0.95rem; font-weight: 600; }
.mono { font-family: monospace; font-size: 0.85rem; }
.tabs-container { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden; }
.tabs { display: flex; border-bottom: 1px solid #e2e8f0; }
.tab { padding: 0.75rem 1.25rem; background: none; border: none; cursor: pointer; font-size: 0.9rem; color: #718096; border-bottom: 2px solid transparent; transition: all 0.2s; }
.tab.active { color: #4299e1; border-bottom-color: #4299e1; font-weight: 500; }
.tab-content { padding: 1rem; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 0.6rem 0.75rem; text-align: left; font-size: 0.78rem; font-weight: 600; color: #718096; text-transform: uppercase; border-bottom: 1px solid #e2e8f0; }
.data-table td { padding: 0.7rem 0.75rem; font-size: 0.88rem; border-bottom: 1px solid #f7fafc; }
.up { color: #38a169; font-weight: 500; }
.down { color: #e53e3e; font-weight: 500; }
.critical { color: #c53030; font-weight: 600; }
.warning { color: #c05621; }
.info { color: #2b6cb0; }
.empty { text-align: center; color: #a0aec0; padding: 2rem !important; }
.pending-notice { background: #fffbf0; border: 1px solid #f6e05e; border-radius: 8px; padding: 1.5rem; text-align: center; color: #744210; }
.loading { text-align: center; padding: 3rem; color: #718096; }
</style>
