<template>
  <div>
    <div class="page-header">
      <div>
        <h2>장비 관리</h2>
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
        <button v-if="selected.size > 0" class="btn-danger" @click="bulkDelete">
          선택 삭제 ({{ selected.size }})
        </button>
        <button v-if="auth.isAdmin" class="btn-primary" @click="showRegister = true">+ 장비 등록</button>
      </div>
    </div>

    <div v-if="loading" class="loading">장비 목록을 불러오는 중...</div>

    <table v-else class="device-table">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>장비명</th>
          <th>IP 주소</th>
          <th>MAC</th>
          <th>프로토콜</th>
          <th>상태</th>
          <th>모델</th>
          <th>마지막 폴링</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filteredDevices.length === 0">
          <td colspan="9" style="text-align: center; color: #718096; padding: 2rem;">등록된 장비가 없습니다.</td>
        </tr>
        <tr
          v-for="device in filteredDevices"
          :key="device.id"
          class="device-row"
          @click="router.push(`/devices/${device.id}`)"
        >
          <td @click.stop><input type="checkbox" :checked="selected.has(device.id)" @change="toggleOne(device.id)" /></td>
          <td><strong>{{ device.name }}</strong></td>
          <td>{{ device.ip_addr }}</td>
          <td class="mono">{{ device.mac_addr }}</td>
          <td><span class="proto-badge">{{ device.protocol }}</span></td>
          <td><StatusBadge :status="device.status" /></td>
          <td>{{ device.model || "—" }}</td>
          <td>{{ device.last_polled_at ? formatTime(device.last_polled_at) : "—" }}</td>
          <td @click.stop>
            <button class="btn-icon" @click="confirmDelete(device)" title="삭제">✕</button>
          </td>
        </tr>
      </tbody>
    </table>

    <RegisterDeviceModal v-if="showRegister" @close="showRegister = false" @created="onDeviceCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useDeviceStore } from "@/stores/device";
import { useTopologyStore } from "@/stores/topology";
import StatusBadge from "@/components/StatusBadge.vue";
import RegisterDeviceModal from "@/components/RegisterDeviceModal.vue";
import api from "@/api/client";

const props = defineProps<{ selectedSiteId?: number; selectedBuildingId?: number }>();

const router = useRouter();
const auth = useAuthStore();
const deviceStore = useDeviceStore();
const topologyStore = useTopologyStore();

const search = ref("");
const statusFilter = ref("");
const showRegister = ref(false);
const selected = ref(new Set<number>());
const loading = computed(() => deviceStore.loading);

const filteredDevices = computed(() => {
  const q = search.value.toLowerCase();
  let list = deviceStore.devices;
  if (statusFilter.value) list = list.filter((d) => d.status === statusFilter.value);
  if (q) list = list.filter((d) => d.name.toLowerCase().includes(q) || d.ip_addr.includes(q));
  return list;
});

const allSelected = computed(() =>
  filteredDevices.value.length > 0 && filteredDevices.value.every((d) => selected.value.has(d.id))
);
function toggleAll(e: Event) {
  if ((e.target as HTMLInputElement).checked) filteredDevices.value.forEach((d) => selected.value.add(d.id));
  else selected.value.clear();
}
function toggleOne(id: number) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id);
}

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

function confirmDelete(device: any) {
  if (confirm(`"${device.name}" 장비를 삭제하시겠습니까?`)) deviceStore.deleteDevice(device.id);
}

async function bulkDelete() {
  if (!confirm(`선택한 ${selected.value.size}개 장비를 삭제하시겠습니까?`)) return;
  await api.post("/devices/bulk-delete", { ids: [...selected.value] });
  selected.value.clear();
  loadDevices();
}

function onDeviceCreated() {
  showRegister.value = false;
  loadDevices();
}

function loadDevices() {
  deviceStore.fetchDevices({ site_id: props.selectedSiteId, building_id: props.selectedBuildingId });
}

watch([() => props.selectedSiteId, () => props.selectedBuildingId], loadDevices);
onMounted(loadDevices);
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
h2 { font-size: 1.3rem; font-weight: 700; }
.breadcrumb { color: #718096; font-size: 0.85rem; margin-top: 0.2rem; }
.header-actions { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.search { padding: 0.45rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; width: 180px; outline: none; }
.search:focus { border-color: #4299e1; }
.filter-select { padding: 0.45rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; background: white; }
.btn-primary { padding: 0.45rem 1rem; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-primary:hover { background: #3182ce; }
.btn-danger { padding: 0.45rem 1rem; background: #e53e3e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.device-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
thead { background: #f7fafc; }
th { padding: 0.75rem 1rem; text-align: left; font-size: 0.8rem; font-weight: 600; color: #718096; text-transform: uppercase; }
td { padding: 0.85rem 1rem; border-top: 1px solid #f0f4f8; font-size: 0.9rem; }
.device-row { cursor: pointer; transition: background 0.1s; }
.device-row:hover td { background: #f7fafc; }
.mono { font-family: monospace; font-size: 0.82rem; }
.proto-badge { background: #e9d8fd; color: #553c9a; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.78rem; font-weight: 500; }
.btn-icon { background: none; border: none; cursor: pointer; color: #a0aec0; font-size: 0.9rem; padding: 0.25rem; }
.btn-icon:hover { color: #e53e3e; }
.loading { text-align: center; padding: 3rem; color: #718096; }
</style>
