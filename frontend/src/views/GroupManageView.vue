<template>
  <div class="page">
    <div class="page-header">
      <h2>그룹 관리</h2>
      <div class="actions">
        <input v-model="search" class="search" placeholder="이름 검색..." />
        <button v-if="selected.size > 0" class="btn-danger" @click="bulkDelete">
          선택 삭제 ({{ selected.size }})
        </button>
        <button v-if="auth.isAdmin" class="btn-primary" @click="openCreate">+ 항목 추가</button>
      </div>
    </div>

    <table class="table">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>유형</th>
          <th>이름</th>
          <th>상위</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td colspan="4" class="empty">항목이 없습니다.</td>
        </tr>
        <tr
          v-for="row in rows"
          :key="`${row.type}-${row.id}`"
          class="data-row"
          @click="openEdit(row)"
          @contextmenu.prevent="openCtx($event, row)"
        >
          <td @click.stop><input type="checkbox" :checked="selected.has(`${row.type}-${row.id}`)" @change="toggleOne(`${row.type}-${row.id}`)" /></td>
          <td><span class="type-badge" :class="row.type">{{ TYPE_LABEL[row.type] }}</span></td>
          <td><strong>{{ row.name }}</strong></td>
          <td class="parent-label">{{ row.parentLabel }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Context menu -->
    <div
      v-if="ctxMenu"
      class="ctx-menu"
      :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
      @click.stop
    >
      <button class="ctx-item danger" @click="confirmDelete(ctxMenu.row); ctxMenu = null">🗑 삭제</button>
    </div>

    <!-- Create Drawer -->
    <DrawerPanel v-model="createOpen" title="항목 추가">
      <div>
        <div class="field">
          <label>유형 *</label>
          <div class="type-tabs">
            <button
              v-for="t in ['group', 'site', 'building'] as const"
              :key="t"
              class="type-tab"
              :class="{ active: createForm.type === t }"
              @click="createForm.type = t"
            >{{ TYPE_LABEL[t] }}</button>
          </div>
        </div>

        <div class="field">
          <label>이름 *</label>
          <input v-model="createForm.name" placeholder="이름 입력" />
        </div>

        <div v-if="createForm.type === 'building'" class="field">
          <label>층수</label>
          <input v-model.number="createForm.floors" type="number" min="1" />
        </div>

        <div v-if="createForm.type === 'site'" class="field">
          <label>상위 그룹 *</label>
          <select v-model="createForm.parentId">
            <option :value="null" disabled>그룹 선택</option>
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </div>

        <div v-if="createForm.type === 'building'" class="field">
          <label>상위 그룹 *</label>
          <select v-model="createForm.groupId" @change="createForm.parentId = null">
            <option :value="null" disabled>그룹 선택</option>
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <label style="margin-top:0.5rem">상위 사이트 *</label>
          <select v-model="createForm.parentId">
            <option :value="null" disabled>사이트 선택</option>
            <option
              v-for="s in sitesOfGroup(createForm.groupId)"
              :key="s.id" :value="s.id"
            >{{ s.name }}</option>
          </select>
        </div>

        <div v-if="createError" class="error-msg">{{ createError }}</div>
      </div>

      <template #footer>
        <button class="btn-cancel" @click="createOpen = false">취소</button>
        <button class="btn-save" @click="submitCreate" :disabled="createLoading">
          {{ createLoading ? "추가 중..." : "추가" }}
        </button>
      </template>
    </DrawerPanel>

    <!-- Edit Drawer -->
    <DrawerPanel v-model="editOpen" :title="`${editForm ? TYPE_LABEL[editForm.type] : ''} 수정`">
      <div v-if="editForm">
        <div class="field">
          <label>이름 *</label>
          <input v-model="editForm.name" placeholder="이름" />
        </div>

        <div v-if="editForm.type === 'site'" class="field">
          <label>상위 그룹</label>
          <select v-model="editForm.parentId">
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </div>

        <div v-if="editForm.type === 'building'" class="field">
          <label>층수</label>
          <input v-model.number="editForm.floors" type="number" min="1" />
        </div>

        <div v-if="editForm.type === 'building'" class="field">
          <label>상위 그룹</label>
          <select v-model="editForm.groupId" @change="editForm.parentId = null">
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <label style="margin-top:0.5rem">상위 사이트</label>
          <select v-model="editForm.parentId">
            <option :value="null" disabled>사이트 선택</option>
            <option
              v-for="s in sitesOfGroup(editForm.groupId)"
              :key="s.id" :value="s.id"
            >{{ s.name }}</option>
          </select>
        </div>

        <div v-if="editError" class="error-msg">{{ editError }}</div>
      </div>

      <template #footer>
        <button class="btn-cancel" @click="editOpen = false">취소</button>
        <button class="btn-save" @click="submitEdit" :disabled="editLoading">
          {{ editLoading ? "저장 중..." : "저장" }}
        </button>
      </template>
    </DrawerPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useTopologyStore, type Site } from "@/stores/topology";
import api from "@/api/client";
import DrawerPanel from "@/components/DrawerPanel.vue";

const auth = useAuthStore();
const topo = useTopologyStore();

const search = ref("");
const selected = ref(new Set<string>());

const TYPE_LABEL: Record<string, string> = { group: "그룹", site: "사이트", building: "건물" };

interface Row {
  type: "group" | "site" | "building";
  id: number;
  name: string;
  parentLabel: string;
  parentId?: number;
  groupId?: number;
  floors?: number;
}

const rows = computed((): Row[] => {
  const q = search.value.toLowerCase();
  const result: Row[] = [];
  for (const g of topo.groups) {
    if (!q || g.name.toLowerCase().includes(q))
      result.push({ type: "group", id: g.id, name: g.name, parentLabel: "—" });
    for (const s of g.sites) {
      if (!q || s.name.toLowerCase().includes(q))
        result.push({ type: "site", id: s.id, name: s.name, parentLabel: g.name, parentId: g.id });
      for (const b of s.buildings) {
        if (!q || b.name.toLowerCase().includes(q))
          result.push({ type: "building", id: b.id, name: b.name, parentLabel: `${g.name} / ${s.name}`, parentId: s.id, groupId: g.id, floors: b.floors });
      }
    }
  }
  return result;
});

const allSelected = computed(() =>
  rows.value.length > 0 && rows.value.every((r) => selected.value.has(`${r.type}-${r.id}`))
);
function toggleAll(e: Event) {
  if ((e.target as HTMLInputElement).checked) rows.value.forEach((r) => selected.value.add(`${r.type}-${r.id}`));
  else selected.value.clear();
}
function toggleOne(key: string) {
  selected.value.has(key) ? selected.value.delete(key) : selected.value.add(key);
}

function sitesOfGroup(groupId: number | null): Site[] {
  if (!groupId) return [];
  return topo.groups.find((g) => g.id === groupId)?.sites ?? [];
}

// Context menu
interface CtxMenu { x: number; y: number; row: Row }
const ctxMenu = ref<CtxMenu | null>(null);
function openCtx(e: MouseEvent, row: Row) { ctxMenu.value = { x: e.clientX, y: e.clientY, row }; }
function closeCtx() { ctxMenu.value = null; }
onMounted(() => document.addEventListener("click", closeCtx));
onUnmounted(() => document.removeEventListener("click", closeCtx));

// Create drawer
interface CreateForm { type: "group" | "site" | "building"; name: string; floors: number; parentId: number | null; groupId: number | null }
const createOpen = ref(false);
const createForm = ref<CreateForm>({ type: "group", name: "", floors: 1, parentId: null, groupId: null });
const createError = ref("");
const createLoading = ref(false);

function openCreate() {
  createForm.value = { type: "group", name: "", floors: 1, parentId: null, groupId: null };
  createError.value = "";
  createOpen.value = true;
}

async function submitCreate() {
  const f = createForm.value;
  if (!f.name.trim()) { createError.value = "이름을 입력하세요."; return; }
  if (f.type === "site" && !f.parentId) { createError.value = "상위 그룹을 선택하세요."; return; }
  if (f.type === "building" && !f.parentId) { createError.value = "상위 사이트를 선택하세요."; return; }
  createLoading.value = true;
  createError.value = "";
  try {
    if (f.type === "group") await topo.createGroup(f.name);
    else if (f.type === "site") await topo.createSite(f.parentId!, f.name);
    else await topo.createBuilding(f.parentId!, f.name, f.floors);
    await topo.fetchGroups();
    createOpen.value = false;
  } catch (e: any) {
    createError.value = e.response?.data?.detail || "오류가 발생했습니다.";
  } finally {
    createLoading.value = false;
  }
}

// Edit drawer
interface EditForm { type: "group" | "site" | "building"; id: number; name: string; parentId: number | null; groupId: number | null; floors: number }
const editOpen = ref(false);
const editForm = ref<EditForm | null>(null);
const editError = ref("");
const editLoading = ref(false);

function openEdit(row: Row) {
  editForm.value = {
    type: row.type, id: row.id, name: row.name,
    parentId: row.parentId ?? null,
    groupId: row.groupId ?? null,
    floors: row.floors ?? 1,
  };
  editError.value = "";
  editOpen.value = true;
}

async function submitEdit() {
  if (!editForm.value) return;
  const f = editForm.value;
  if (!f.name.trim()) { editError.value = "이름을 입력하세요."; return; }
  editLoading.value = true;
  editError.value = "";
  try {
    if (f.type === "group") {
      await api.patch(`/groups/${f.id}`, { name: f.name });
    } else if (f.type === "site") {
      await api.patch(`/sites/${f.id}`, { name: f.name, group_id: f.parentId });
    } else {
      await api.patch(`/buildings/${f.id}`, { name: f.name, floors: f.floors, site_id: f.parentId });
    }
    await topo.fetchGroups();
    editOpen.value = false;
  } catch (e: any) {
    editError.value = e.response?.data?.detail || "오류가 발생했습니다.";
  } finally {
    editLoading.value = false;
  }
}

// Delete
async function confirmDelete(row: Row) {
  if (!confirm(`"${row.name}"을(를) 삭제하시겠습니까? 하위 항목도 모두 삭제됩니다.`)) return;
  if (row.type === "group") await topo.deleteGroup(row.id);
  else if (row.type === "site") await topo.deleteSite(row.id);
  else await topo.deleteBuilding(row.id);
  await topo.fetchGroups();
}

async function bulkDelete() {
  if (!confirm(`선택한 ${selected.value.size}개 항목을 삭제하시겠습니까?`)) return;
  const groups = [...selected.value].filter((k) => k.startsWith("group-")).map((k) => +k.split("-")[1]);
  const sites = [...selected.value].filter((k) => k.startsWith("site-")).map((k) => +k.split("-")[1]);
  const buildings = [...selected.value].filter((k) => k.startsWith("building-")).map((k) => +k.split("-")[1]);
  if (groups.length) await api.post("/groups/bulk-delete", { ids: groups });
  if (sites.length) await api.post("/sites/bulk-delete", { ids: sites });
  if (buildings.length) await api.post("/buildings/bulk-delete", { ids: buildings });
  await topo.fetchGroups();
  selected.value.clear();
}

onMounted(() => topo.fetchGroups());
</script>

<style scoped>
.page { max-width: 860px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.page-header h2 { font-size: 1.15rem; font-weight: 700; }
.actions { display: flex; gap: 0.6rem; align-items: center; }
.search { padding: 0.45rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; width: 180px; outline: none; }
.search:focus { border-color: #4299e1; }
.btn-primary { padding: 0.45rem 1rem; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-danger { padding: 0.45rem 1rem; background: #e53e3e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }

.table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.table th { background: #f7fafc; padding: 0.75rem 1rem; text-align: left; font-size: 0.82rem; color: #4a5568; font-weight: 600; border-bottom: 1px solid #e2e8f0; }
.table td { padding: 0.7rem 1rem; border-bottom: 1px solid #f0f4f8; font-size: 0.9rem; }
.table tr:last-child td { border-bottom: none; }
.empty { text-align: center; color: #a0aec0; padding: 2rem !important; }
.data-row { cursor: pointer; transition: background 0.1s; }
.data-row:hover td { background: #f7fafc; }

.type-badge { padding: 0.15rem 0.5rem; border-radius: 10px; font-size: 0.78rem; font-weight: 600; }
.type-badge.group { background: #e0e7ff; color: #3730a3; }
.type-badge.site { background: #d1fae5; color: #065f46; }
.type-badge.building { background: #fef3c7; color: #92400e; }
.parent-label { color: #718096; font-size: 0.85rem; }

/* Context menu */
.ctx-menu {
  position: fixed; background: white; border: 1px solid #e2e8f0;
  border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 500; min-width: 120px; overflow: hidden;
}
.ctx-item {
  display: block; width: 100%; padding: 0.6rem 1rem; background: none;
  border: none; text-align: left; font-size: 0.88rem; cursor: pointer; color: #2d3748;
}
.ctx-item:hover { background: #f7fafc; }
.ctx-item.danger { color: #e53e3e; }
.ctx-item.danger:hover { background: #fff5f5; }

/* Drawer content */
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.85rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: #4a5568; }
.field input, .field select { padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; outline: none; }
.field input:focus, .field select:focus { border-color: #4299e1; }

.type-tabs { display: flex; gap: 0.4rem; }
.type-tab { padding: 0.4rem 1rem; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-size: 0.88rem; background: white; color: #4a5568; }
.type-tab.active { background: #ebf8ff; border-color: #4299e1; color: #2b6cb0; font-weight: 600; }

.error-msg { color: #e53e3e; font-size: 0.85rem; margin-top: 0.5rem; }
.btn-save { padding: 0.5rem 1.25rem; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-save:hover { background: #3182ce; }
.btn-save:disabled { background: #a0aec0; cursor: not-allowed; }
.btn-cancel { padding: 0.5rem 1.25rem; background: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-cancel:hover { background: #cbd5e0; }
</style>
