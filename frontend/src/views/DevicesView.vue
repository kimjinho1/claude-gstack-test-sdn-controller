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
        </tr>
      </thead>
      <tbody>
        <tr v-if="filteredDevices.length === 0">
          <td colspan="8" style="text-align: center; color: #718096; padding: 2rem;">등록된 장비가 없습니다.</td>
        </tr>
        <tr
          v-for="device in filteredDevices"
          :key="device.id"
          class="device-row"
          @click="openDetail(device)"
          @contextmenu.prevent="openCtx($event, device)"
        >
          <td @click.stop><input type="checkbox" :checked="selected.has(device.id)" @change="toggleOne(device.id)" /></td>
          <td><strong>{{ device.name }}</strong></td>
          <td>{{ device.ip_addr }}</td>
          <td class="mono">{{ device.mac_addr }}</td>
          <td><span class="proto-badge">{{ device.protocol }}</span></td>
          <td><StatusBadge :status="device.status" /></td>
          <td>{{ device.model || "—" }}</td>
          <td>{{ device.last_polled_at ? formatTime(device.last_polled_at) : "—" }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Context Menu -->
    <div
      v-if="ctxMenu.item"
      class="ctx-menu"
      :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
    >
      <button class="ctx-item ctx-danger" @click="confirmDelete(ctxMenu.item!)">삭제</button>
    </div>

    <!-- Device Detail Drawer -->
    <DrawerPanel v-model="drawerOpen" :title="drawerDevice?.name || '장비 정보'" :width="480">
      <div v-if="drawerDevice" class="detail-body">
        <div class="detail-section">
          <h4>기본 정보</h4>
          <div class="detail-grid">
            <span class="label">장비명</span><span>{{ drawerDevice.name }}</span>
            <span class="label">IP 주소</span><span class="mono">{{ drawerDevice.ip_addr }}</span>
            <span class="label">MAC 주소</span><span class="mono">{{ drawerDevice.mac_addr }}</span>
            <span class="label">프로토콜</span><span><span class="proto-badge">{{ drawerDevice.protocol }}</span></span>
            <span class="label">상태</span><span><StatusBadge :status="drawerDevice.status" /></span>
          </div>
        </div>
        <div class="detail-section" v-if="drawerDevice.model || drawerDevice.serial_no || drawerDevice.sw_version || drawerDevice.uptime">
          <h4>장비 상세</h4>
          <div class="detail-grid">
            <span class="label">모델</span><span>{{ drawerDevice.model || "—" }}</span>
            <span class="label">시리얼 번호</span><span class="mono">{{ drawerDevice.serial_no || "—" }}</span>
            <span class="label">SW 버전</span><span>{{ drawerDevice.sw_version || "—" }}</span>
            <span class="label">업타임</span><span>{{ drawerDevice.uptime || "—" }}</span>
          </div>
        </div>
        <div class="detail-section">
          <h4>폴링 정보</h4>
          <div class="detail-grid">
            <span class="label">마지막 폴링</span>
            <span>{{ drawerDevice.last_polled_at ? formatTime(drawerDevice.last_polled_at) : "—" }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="drawerOpen = false">닫기</button>
        <button class="btn-primary" @click="goToDetail">상세 보기 →</button>
      </template>
    </DrawerPanel>

    <RegisterDeviceModal v-if="showRegister" @close="showRegister = false" @created="onDeviceCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useDeviceStore } from "@/stores/device";
import { useTopologyStore } from "@/stores/topology";
import StatusBadge from "@/components/StatusBadge.vue";
import DrawerPanel from "@/components/DrawerPanel.vue";
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

// Context menu
const ctxMenu = ref<{ x: number; y: number; item: any | null }>({ x: 0, y: 0, item: null });
function openCtx(e: MouseEvent, device: any) {
  ctxMenu.value = { x: e.clientX, y: e.clientY, item: device };
}
function closeCtx() {
  ctxMenu.value.item = null;
}
onMounted(() => document.addEventListener("click", closeCtx));
onUnmounted(() => document.removeEventListener("click", closeCtx));

// Drawer
const drawerOpen = ref(false);
const drawerDevice = ref<any | null>(null);
function openDetail(device: any) {
  drawerDevice.value = device;
  drawerOpen.value = true;
}
function goToDetail() {
  if (drawerDevice.value) router.push(`/devices/${drawerDevice.value.id}`);
}

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
  ctxMenu.value.item = null;
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
.btn-secondary { padding: 0.45rem 1rem; background: white; color: #4a5568; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-secondary:hover { background: #f7fafc; }
.btn-danger { padding: 0.45rem 1rem; background: #e53e3e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.device-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
thead { background: #f7fafc; }
th { padding: 0.75rem 1rem; text-align: left; font-size: 0.8rem; font-weight: 600; color: #718096; text-transform: uppercase; }
td { padding: 0.85rem 1rem; border-top: 1px solid #f0f4f8; font-size: 0.9rem; }
.device-row { cursor: pointer; transition: background 0.1s; }
.device-row:hover td { background: #f7fafc; }
.mono { font-family: monospace; font-size: 0.82rem; }
.proto-badge { background: #e9d8fd; color: #553c9a; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.78rem; font-weight: 500; }
.loading { text-align: center; padding: 3rem; color: #718096; }

/* Context menu */
.ctx-menu {
  position: fixed;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  z-index: 500;
  min-width: 100px;
  padding: 0.25rem 0;
}
.ctx-item {
  display: block;
  width: 100%;
  padding: 0.5rem 1rem;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: 0.875rem;
  color: #2d3748;
}
.ctx-item:hover { background: #f7fafc; }
.ctx-danger { color: #e53e3e; }
.ctx-danger:hover { background: #fff5f5; }

/* Drawer detail content */
.detail-body { display: flex; flex-direction: column; gap: 1.5rem; }
.detail-section h4 { font-size: 0.78rem; font-weight: 700; color: #718096; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 0.75rem; }
.detail-grid { display: grid; grid-template-columns: 7rem 1fr; gap: 0.5rem 1rem; align-items: center; }
.label { font-size: 0.85rem; color: #718096; }
</style>
