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
          <td colspan="8" class="empty-row">등록된 장비가 없습니다.</td>
        </tr>
        <tr
          v-for="device in filteredDevices"
          :key="device.id"
          class="device-row"
          @click="openEdit(device)"
          @contextmenu.prevent="openCtx($event, device)"
        >
          <td @click.stop><input type="checkbox" :checked="selected.has(device.id)" @change="toggleOne(device.id)" /></td>
          <td><strong>{{ device.name }}</strong></td>
          <td class="mono">{{ device.ip_addr }}</td>
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

    <!-- Device Edit Drawer -->
    <DrawerPanel v-model="drawerOpen" :title="editForm ? editForm.name || '장비 정보' : '장비 정보'" :width="480">
      <div v-if="editForm" class="drawer-content">

        <!-- Read-only info section -->
        <div class="info-section">
          <div class="section-heading">장비 현황</div>
          <div class="info-grid">
            <span class="info-label">IP 주소</span><span class="mono">{{ editForm._device.ip_addr }}</span>
            <span class="info-label">MAC 주소</span><span class="mono">{{ editForm._device.mac_addr }}</span>
            <span class="info-label">프로토콜</span><span><span class="proto-badge">{{ editForm._device.protocol }}</span></span>
            <span class="info-label">상태</span><span><StatusBadge :status="editForm._device.status" /></span>
            <template v-if="editForm._device.model">
              <span class="info-label">모델</span><span>{{ editForm._device.model }}</span>
            </template>
            <template v-if="editForm._device.uptime">
              <span class="info-label">업타임</span><span>{{ editForm._device.uptime }}</span>
            </template>
            <template v-if="editForm._device.last_polled_at">
              <span class="info-label">마지막 폴링</span><span>{{ formatTime(editForm._device.last_polled_at) }}</span>
            </template>
          </div>
        </div>

        <div class="divider" />

        <!-- Editable fields -->
        <div class="section-heading">정보 수정</div>

        <div class="form-field">
          <label class="form-label">장비명</label>
          <input v-model="editForm.name" class="form-input" placeholder="장비명" />
        </div>

        <div class="form-field">
          <label class="form-label">층 (Floor)</label>
          <input v-model.number="editForm.floor" class="form-input" type="number" placeholder="예: 3" />
        </div>

        <!-- SSH credentials -->
        <template v-if="editForm._device.protocol === 'SSH'">
          <div class="section-heading" style="margin-top: 1rem;">SSH 자격증명</div>
          <div class="form-field">
            <label class="form-label">SSH 사용자 ID</label>
            <input v-model="editForm.ssh_id" class="form-input" placeholder="admin" />
          </div>
          <div class="form-field">
            <label class="form-label">SSH 비밀번호 <span class="hint">(변경 시 입력)</span></label>
            <input v-model="editForm.ssh_password" class="form-input" type="password" placeholder="변경하지 않으면 비워두세요" />
          </div>
          <div class="form-field">
            <label class="form-label">SSH 포트</label>
            <input v-model.number="editForm.ssh_port" class="form-input" type="number" placeholder="22" />
          </div>
        </template>

        <!-- REST credentials -->
        <template v-else-if="editForm._device.protocol === 'REST'">
          <div class="section-heading" style="margin-top: 1rem;">REST 자격증명</div>
          <div class="form-field">
            <label class="form-label">REST 사용자 ID</label>
            <input v-model="editForm.rest_id" class="form-input" placeholder="admin" />
          </div>
          <div class="form-field">
            <label class="form-label">REST 비밀번호 <span class="hint">(변경 시 입력)</span></label>
            <input v-model="editForm.rest_password" class="form-input" type="password" placeholder="변경하지 않으면 비워두세요" />
          </div>
          <div class="form-field">
            <label class="form-label">REST 포트</label>
            <input v-model.number="editForm.rest_port" class="form-input" type="number" placeholder="443" />
          </div>
        </template>

        <!-- Topology parent link -->
        <div class="divider" />
        <div class="section-heading">토폴로지 링크</div>
        <div class="form-field">
          <label class="form-label">상위 장비 (부모)</label>
          <select v-model="editForm.parent_id" class="form-input">
            <option :value="null">없음 (독립 장비)</option>
            <option v-for="d in otherDevices" :key="d.id" :value="d.id">
              {{ d.name }} — {{ d.ip_addr }}
            </option>
          </select>
        </div>

        <div v-if="editError" class="error-msg">{{ editError }}</div>
      </div>

      <template #footer>
        <button class="btn-link" @click="goToDetail">상세 보기 →</button>
        <button class="btn-secondary" @click="drawerOpen = false">취소</button>
        <button class="btn-primary" @click="submitEdit" :disabled="editLoading">
          {{ editLoading ? "저장 중..." : "저장" }}
        </button>
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

// Edit drawer
interface EditForm {
  _device: any;
  name: string;
  floor: number | null;
  ssh_id: string;
  ssh_password: string;
  ssh_port: number | null;
  rest_id: string;
  rest_password: string;
  rest_port: number | null;
  parent_id: number | null;
  _parentLinkId: number | null;
}

const drawerOpen = ref(false);
const editForm = ref<EditForm | null>(null);
const editError = ref("");
const editLoading = ref(false);

const otherDevices = computed(() =>
  editForm.value ? deviceStore.devices.filter((d) => d.id !== editForm.value!._device.id) : []
);

async function openEdit(device: any) {
  editError.value = "";
  // Fetch current parent link (where child_id == this device)
  let parent_id: number | null = null;
  let _parentLinkId: number | null = null;
  try {
    const { data } = await api.get("/device-links");
    const parentLink = data.find((l: any) => l.child_id === device.id);
    if (parentLink) { parent_id = parentLink.parent_id; _parentLinkId = parentLink.id; }
  } catch { /* ignore */ }

  editForm.value = {
    _device: device,
    name: device.name,
    floor: device.floor ?? null,
    ssh_id: device.ssh_id ?? "",
    ssh_password: "",
    ssh_port: device.ssh_port ?? 22,
    rest_id: device.rest_id ?? "",
    rest_password: "",
    rest_port: device.rest_port ?? null,
    parent_id,
    _parentLinkId,
  };
  drawerOpen.value = true;
}

function goToDetail() {
  if (editForm.value) router.push(`/devices/${editForm.value._device.id}`);
}

async function submitEdit() {
  if (!editForm.value) return;
  if (!editForm.value.name.trim()) { editError.value = "장비명을 입력하세요."; return; }

  editLoading.value = true;
  editError.value = "";
  try {
    const payload: Record<string, any> = {
      name: editForm.value.name,
    };
    if (editForm.value.floor != null) payload.floor = editForm.value.floor;

    if (editForm.value._device.protocol === "SSH") {
      if (editForm.value.ssh_id) payload.ssh_id = editForm.value.ssh_id;
      if (editForm.value.ssh_password) payload.ssh_password = editForm.value.ssh_password;
      if (editForm.value.ssh_port != null) payload.ssh_port = editForm.value.ssh_port;
    } else if (editForm.value._device.protocol === "REST") {
      if (editForm.value.rest_id) payload.rest_id = editForm.value.rest_id;
      if (editForm.value.rest_password) payload.rest_password = editForm.value.rest_password;
      if (editForm.value.rest_port != null) payload.rest_port = editForm.value.rest_port;
    }

    await api.patch(`/devices/${editForm.value._device.id}`, payload);

    // Handle parent link change
    const newParentId = editForm.value.parent_id;
    const oldParentLinkId = editForm.value._parentLinkId;
    const oldParentId = oldParentLinkId
      ? ((await api.get("/device-links")).data.find((l: any) => l.id === oldParentLinkId)?.parent_id ?? null)
      : null;

    if (newParentId !== oldParentId) {
      if (oldParentLinkId) await api.delete(`/device-links/${oldParentLinkId}`);
      if (newParentId) {
        await api.post("/device-links", {
          parent_id: newParentId,
          child_id: editForm.value._device.id,
        });
      }
    }

    drawerOpen.value = false;
    loadDevices();
  } catch (e: any) {
    editError.value = e.response?.data?.detail || "저장에 실패했습니다.";
  } finally {
    editLoading.value = false;
  }
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
/* ── Layout ── */
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
h2 { font-size: 1.1rem; font-weight: 700; color: #d4dbe4; text-transform: uppercase; letter-spacing: 0.05em; }
.breadcrumb { color: #6a8099; font-size: 0.82rem; margin-top: 0.2rem; }
.header-actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; justify-content: flex-end; }

/* ── Inputs ── */
.search {
  padding: 0.4rem 0.7rem; border: 1px solid #2a3a4a; border-radius: 2px;
  font-size: 0.87rem; width: 180px; outline: none; color: #d4dbe4;
  background: #0e1a26;
}
.search:focus { border-color: #1d6fa4; }
.search::placeholder { color: #4a6075; }
.filter-select {
  padding: 0.4rem 0.7rem; border: 1px solid #2a3a4a; border-radius: 2px;
  font-size: 0.87rem; background: #0e1a26; color: #d4dbe4; outline: none;
}
.filter-select:focus { border-color: #1d6fa4; }

/* ── Buttons ── */
.btn-primary {
  padding: 0.4rem 0.9rem; background: #1d6fa4; color: white; border: none;
  border-radius: 2px; cursor: pointer; font-size: 0.87rem; font-weight: 600;
  transition: background 0.15s;
}
.btn-primary:hover { background: #2585c2; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  padding: 0.4rem 0.9rem; background: transparent; color: #8fa0b4;
  border: 1px solid #2a3a4a; border-radius: 2px; cursor: pointer; font-size: 0.87rem;
  transition: all 0.15s;
}
.btn-secondary:hover { background: #1a2a3a; color: #d4dbe4; }
.btn-danger {
  padding: 0.4rem 0.9rem; background: #3a0a0a; color: #db3737; border: 1px solid #8b2222;
  border-radius: 2px; cursor: pointer; font-size: 0.87rem; font-weight: 600;
  transition: all 0.15s;
}
.btn-danger:hover { background: #5a1212; }
.btn-link {
  padding: 0.4rem 0.5rem; background: none; border: none; color: #4dacf7;
  cursor: pointer; font-size: 0.87rem; margin-right: auto;
}
.btn-link:hover { text-decoration: underline; }

/* ── Table ── */
.device-table { width: 100%; border-collapse: collapse; background: #111c27; border: 1px solid #1e2d3a; border-radius: 3px; }
thead { background: #0d1720; }
th {
  padding: 0.6rem 1rem; text-align: left; font-size: 0.7rem; font-weight: 700;
  color: #6a8099; text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid #1e2d3a;
}
td { padding: 0.72rem 1rem; border-top: 1px solid #172534; font-size: 0.87rem; color: #c4d0dc; }
.device-row { cursor: pointer; transition: background 0.1s; }
.device-row:hover td { background: #172534; }
.empty-row { text-align: center; color: #4a6075; padding: 2.5rem 1rem !important; }
.mono { font-family: 'Consolas', 'Monaco', monospace; font-size: 0.82rem; color: #8fa0b4; }
.proto-badge {
  background: #0d2a45; color: #5aabdb; padding: 0.15rem 0.5rem;
  border-radius: 2px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
}
.loading { text-align: center; padding: 3rem; color: #6a8099; }

/* ── Context menu ── */
.ctx-menu {
  position: fixed; background: #131f2b; border: 1px solid #2a3a4a;
  border-radius: 3px; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  z-index: 500; min-width: 110px; padding: 0.25rem 0;
}
.ctx-item {
  display: block; width: 100%; padding: 0.5rem 1rem; background: none;
  border: none; text-align: left; cursor: pointer; font-size: 0.85rem; color: #c4d0dc;
}
.ctx-item:hover { background: #1a2a3a; }
.ctx-danger { color: #db3737; }
.ctx-danger:hover { background: #2e0a0a; }

/* ── Drawer content ── */
.drawer-content { display: flex; flex-direction: column; }
.section-heading {
  font-size: 0.7rem; font-weight: 700; color: #6a8099;
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.8rem;
}
.divider { border: none; border-top: 1px solid #1e2d3a; margin: 1.2rem 0; }

.info-section { margin-bottom: 0; }
.info-grid { display: grid; grid-template-columns: 7.5rem 1fr; gap: 0.5rem 1rem; align-items: center; }
.info-label { font-size: 0.82rem; color: #6a8099; }

.form-field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.8rem; }
.form-label { font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #6a8099; }
.form-input {
  padding: 0.45rem 0.65rem; border: 1px solid #2a3a4a; border-radius: 2px;
  font-size: 0.87rem; color: #d4dbe4; background: #0e1a26; outline: none;
}
.form-input:focus { border-color: #1d6fa4; }
.hint { font-size: 0.73rem; color: #6a8099; font-weight: 400; }
.error-msg { color: #db3737; font-size: 0.82rem; margin-top: 0.75rem; }
</style>
