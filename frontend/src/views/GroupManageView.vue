<template>
  <div class="page">
    <div class="page-header">
      <div class="page-title">
        <h2>그룹 관리</h2>
        <span class="page-subtitle">{{ rows.length }}개 항목</span>
      </div>
      <div class="actions">
        <div class="search-wrap">
          <span class="search-icon">⌕</span>
          <input v-model="search" class="search" placeholder="이름 검색..." />
        </div>
        <button v-if="selected.size > 0" class="btn-danger" @click="bulkDelete">
          삭제 ({{ selected.size }})
        </button>
        <button v-if="auth.isAdmin" class="btn-primary" @click="openCreate">＋ 항목 추가</button>
      </div>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th class="th-check"><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
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
            <td class="td-check" @click.stop>
              <input type="checkbox" :checked="selected.has(`${row.type}-${row.id}`)" @change="toggleOne(`${row.type}-${row.id}`)" />
            </td>
            <td><span class="type-badge" :class="row.type">{{ TYPE_LABEL[row.type] }}</span></td>
            <td class="td-name">{{ row.name }}</td>
            <td class="td-parent">{{ row.parentLabel }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Context menu -->
    <div
      v-if="ctxMenu"
      class="ctx-menu"
      :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
      @click.stop
    >
      <button class="ctx-item danger" @click="confirmDelete(ctxMenu.row); ctxMenu = null">삭제</button>
    </div>

    <!-- Create Drawer -->
    <DrawerPanel v-model="createOpen" title="항목 추가">
      <div class="form">
        <div class="form-field">
          <label class="form-label">유형</label>
          <div class="type-tabs">
            <button
              v-for="t in ['group', 'site', 'building'] as const"
              :key="t"
              class="type-tab"
              :class="{ active: createForm.type === t }"
              @click="createForm.type = t; createForm.parentId = null"
            >{{ TYPE_LABEL[t] }}</button>
          </div>
        </div>

        <div class="form-field">
          <label class="form-label">이름 <span class="required">*</span></label>
          <input v-model="createForm.name" class="form-input" placeholder="이름 입력" />
        </div>

        <div v-if="createForm.type === 'building'" class="form-field">
          <label class="form-label">층수</label>
          <input v-model.number="createForm.floors" class="form-input" type="number" min="1" />
        </div>

        <div v-if="createForm.type === 'site'" class="form-field">
          <label class="form-label">상위 그룹 <span class="required">*</span></label>
          <select v-model="createForm.parentId" class="form-select">
            <option :value="null" disabled>그룹 선택</option>
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </div>

        <div v-if="createForm.type === 'building'" class="form-field">
          <label class="form-label">상위 사이트 <span class="required">*</span></label>
          <select v-model="createForm.parentId" class="form-select">
            <option :value="null" disabled>사이트 선택</option>
            <option v-for="s in allSites" :key="s.id" :value="s.id">
              {{ s.groupName }} / {{ s.name }}
            </option>
          </select>
        </div>

        <p v-if="createError" class="error-msg">{{ createError }}</p>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="createOpen = false">취소</button>
        <button class="btn-primary" @click="submitCreate" :disabled="createLoading">
          {{ createLoading ? "추가 중..." : "추가" }}
        </button>
      </template>
    </DrawerPanel>

    <!-- Edit Drawer -->
    <DrawerPanel v-model="editOpen" :title="`${editForm ? TYPE_LABEL[editForm.type] : ''} 수정`">
      <div v-if="editForm" class="form">
        <div class="form-field">
          <label class="form-label">이름 <span class="required">*</span></label>
          <input v-model="editForm.name" class="form-input" placeholder="이름" />
        </div>

        <div v-if="editForm.type === 'building'" class="form-field">
          <label class="form-label">층수</label>
          <input v-model.number="editForm.floors" class="form-input" type="number" min="1" />
        </div>

        <div v-if="editForm.type === 'site'" class="form-field">
          <label class="form-label">상위 그룹</label>
          <select v-model="editForm.parentId" class="form-select">
            <option v-for="g in topo.groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </div>

        <div v-if="editForm.type === 'building'" class="form-field">
          <label class="form-label">상위 사이트</label>
          <select v-model="editForm.parentId" class="form-select">
            <option :value="null" disabled>사이트 선택</option>
            <option v-for="s in allSites" :key="s.id" :value="s.id">
              {{ s.groupName }} / {{ s.name }}
            </option>
          </select>
        </div>

        <p v-if="editError" class="error-msg">{{ editError }}</p>
      </div>

      <template #footer>
        <button class="btn-ghost" @click="editOpen = false">취소</button>
        <button class="btn-primary" @click="submitEdit" :disabled="editLoading">
          {{ editLoading ? "저장 중..." : "저장" }}
        </button>
      </template>
    </DrawerPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useTopologyStore } from "@/stores/topology";
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

// All sites flattened (with group name for display)
const allSites = computed(() =>
  topo.groups.flatMap((g) => g.sites.map((s) => ({ ...s, groupName: g.name })))
);

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

// Context menu
interface CtxMenu { x: number; y: number; row: Row }
const ctxMenu = ref<CtxMenu | null>(null);
function openCtx(e: MouseEvent, row: Row) { ctxMenu.value = { x: e.clientX, y: e.clientY, row }; }
function closeCtx() { ctxMenu.value = null; }
onMounted(() => document.addEventListener("click", closeCtx));
onUnmounted(() => document.removeEventListener("click", closeCtx));

// Create drawer
interface CreateForm { type: "group" | "site" | "building"; name: string; floors: number; parentId: number | null }
const createOpen = ref(false);
const createForm = ref<CreateForm>({ type: "group", name: "", floors: 1, parentId: null });
const createError = ref("");
const createLoading = ref(false);

function openCreate() {
  createForm.value = { type: "group", name: "", floors: 1, parentId: null };
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
interface EditForm { type: "group" | "site" | "building"; id: number; name: string; parentId: number | null; floors: number }
const editOpen = ref(false);
const editForm = ref<EditForm | null>(null);
const editError = ref("");
const editLoading = ref(false);

function openEdit(row: Row) {
  editForm.value = {
    type: row.type, id: row.id, name: row.name,
    parentId: row.parentId ?? null,
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
/* ── Layout ─────────────────────────────────────────────── */
.page { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.25rem; padding-bottom: 1rem;
  border-bottom: 1px solid #dce1e7;
}
.page-title { display: flex; align-items: baseline; gap: 0.75rem; }
.page-title h2 { font-size: 1.1rem; font-weight: 600; color: #182026; margin: 0; }
.page-subtitle { font-size: 0.78rem; color: #738694; }

.actions { display: flex; gap: 0.5rem; align-items: center; }

/* ── Search ─────────────────────────────────────────────── */
.search-wrap { position: relative; }
.search-icon {
  position: absolute; left: 0.6rem; top: 50%; transform: translateY(-50%);
  color: #738694; font-size: 1rem; pointer-events: none;
}
.search {
  padding: 0.4rem 0.75rem 0.4rem 2rem; border: 1px solid #c5cdd4;
  border-radius: 2px; font-size: 0.85rem; width: 200px;
  background: #fff; color: #182026; outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.search:focus { border-color: #1d6fa4; box-shadow: 0 0 0 2px rgba(29,111,164,0.18); }

/* ── Buttons ─────────────────────────────────────────────── */
.btn-primary {
  padding: 0.4rem 0.9rem; background: #1d6fa4; color: #fff;
  border: none; border-radius: 2px; cursor: pointer; font-size: 0.85rem;
  font-weight: 500; letter-spacing: 0.01em; transition: background 0.15s;
}
.btn-primary:hover { background: #1a5f8e; }
.btn-primary:disabled { background: #8cbbda; cursor: not-allowed; }

.btn-danger {
  padding: 0.4rem 0.9rem; background: #c23030; color: #fff;
  border: none; border-radius: 2px; cursor: pointer; font-size: 0.85rem;
  transition: background 0.15s;
}
.btn-danger:hover { background: #a82828; }

.btn-ghost {
  padding: 0.4rem 0.9rem; background: transparent; color: #4a6074;
  border: 1px solid #c5cdd4; border-radius: 2px; cursor: pointer; font-size: 0.85rem;
  transition: background 0.15s;
}
.btn-ghost:hover { background: #ebf1f5; }

/* ── Table ─────────────────────────────────────────────── */
.table-wrap {
  background: #fff; border: 1px solid #dce1e7;
  border-radius: 2px; overflow: hidden;
}
.table { width: 100%; border-collapse: collapse; }
.table thead { background: #ebf1f5; }
.table th {
  padding: 0.6rem 1rem; text-align: left;
  font-size: 0.72rem; font-weight: 600; color: #5c7080;
  text-transform: uppercase; letter-spacing: 0.06em;
  border-bottom: 1px solid #dce1e7;
}
.th-check { width: 36px; padding: 0.6rem 0 0.6rem 1rem; }
.table td { padding: 0.65rem 1rem; border-bottom: 1px solid #ebf1f5; font-size: 0.875rem; color: #182026; }
.table tr:last-child td { border-bottom: none; }
.empty { text-align: center; color: #8fafc4; padding: 2.5rem !important; font-size: 0.875rem; }

.td-check { width: 36px; padding: 0.65rem 0 0.65rem 1rem; }
.td-name { font-weight: 500; }
.td-parent { color: #5c7080; font-size: 0.84rem; }

.data-row { cursor: pointer; transition: background 0.1s; }
.data-row:hover td { background: #f5f8fa; }

/* ── Type badges ─────────────────────────────────────────── */
.type-badge {
  display: inline-block; padding: 0.1rem 0.45rem;
  border-radius: 2px; font-size: 0.72rem; font-weight: 600;
  letter-spacing: 0.04em;
}
.type-badge.group { background: #dce9f7; color: #1d4e78; }
.type-badge.site  { background: #d4edda; color: #155724; }
.type-badge.building { background: #fef3cd; color: #856404; }

/* ── Context menu ─────────────────────────────────────────── */
.ctx-menu {
  position: fixed; background: #fff; border: 1px solid #c5cdd4;
  border-radius: 2px; box-shadow: 0 4px 16px rgba(0,0,0,0.14);
  z-index: 500; min-width: 110px; overflow: hidden;
}
.ctx-item {
  display: block; width: 100%; padding: 0.55rem 1rem;
  background: none; border: none; text-align: left;
  font-size: 0.85rem; cursor: pointer; color: #182026;
}
.ctx-item:hover { background: #f5f8fa; }
.ctx-item.danger { color: #c23030; }
.ctx-item.danger:hover { background: #fdf0f0; }

/* ── Drawer form ─────────────────────────────────────────── */
.form { display: flex; flex-direction: column; gap: 1rem; }
.form-field { display: flex; flex-direction: column; gap: 0.35rem; }
.form-label { font-size: 0.78rem; font-weight: 600; color: #5c7080; text-transform: uppercase; letter-spacing: 0.05em; }
.required { color: #c23030; }

.form-input, .form-select {
  padding: 0.45rem 0.7rem; border: 1px solid #c5cdd4;
  border-radius: 2px; font-size: 0.875rem; color: #182026;
  background: #fff; outline: none; transition: border-color 0.15s, box-shadow 0.15s;
  width: 100%;
}
.form-input:focus, .form-select:focus {
  border-color: #1d6fa4; box-shadow: 0 0 0 2px rgba(29,111,164,0.18);
}

.type-tabs { display: flex; gap: 0; border: 1px solid #c5cdd4; border-radius: 2px; overflow: hidden; }
.type-tab {
  flex: 1; padding: 0.4rem 0.6rem; border: none;
  background: #fff; cursor: pointer; font-size: 0.84rem; color: #5c7080;
  border-right: 1px solid #c5cdd4; transition: background 0.12s, color 0.12s;
}
.type-tab:last-child { border-right: none; }
.type-tab.active { background: #1d6fa4; color: #fff; font-weight: 600; }
.type-tab:not(.active):hover { background: #ebf1f5; }

.error-msg { color: #c23030; font-size: 0.82rem; margin: 0; }
</style>
