<template>
  <div class="page">
    <div class="page-header">
      <h2>그룹 관리</h2>
      <div class="actions">
        <input v-model="search" class="search" placeholder="이름 검색..." />
        <button v-if="selected.size > 0" class="btn-danger" @click="bulkDelete">
          선택 삭제 ({{ selected.size }})
        </button>
        <button v-if="auth.isAdmin" class="btn-primary" @click="openCreate('group')">+ 그룹 추가</button>
      </div>
    </div>

    <!-- Flat table of all groups/sites/buildings -->
    <table class="table">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>유형</th>
          <th>이름</th>
          <th>상위</th>
          <th>작업</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td colspan="5" class="empty">항목이 없습니다.</td>
        </tr>
        <template v-for="row in rows" :key="`${row.type}-${row.id}`">
          <tr>
            <td><input type="checkbox" :checked="selected.has(`${row.type}-${row.id}`)" @change="toggleOne(`${row.type}-${row.id}`)" /></td>
            <td><span class="type-badge" :class="row.type">{{ TYPE_LABEL[row.type] }}</span></td>
            <td class="name-cell">
              <span v-if="editTarget?.key !== `${row.type}-${row.id}`" class="name-text">{{ row.name }}</span>
              <input v-else v-model="editTarget.name" class="inline-edit" @keyup.enter="saveInlineEdit" @keyup.escape="editTarget = null" @blur="saveInlineEdit" autofocus />
            </td>
            <td class="parent-cell">{{ row.parentLabel }}</td>
            <td class="row-actions">
              <button v-if="row.type === 'group'" class="btn-sm" @click="openCreate('site', row)">사이트+</button>
              <button v-if="row.type === 'site'" class="btn-sm" @click="openCreate('building', row)">건물+</button>
              <button class="btn-sm" @click="startInlineEdit(row)">이름 수정</button>
              <button class="btn-sm danger" @click="confirmDelete(row)">삭제</button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <!-- Add Modal -->
    <div v-if="createModal" class="modal-overlay" @click.self="createModal = null">
      <div class="modal">
        <h3>{{ createModal.title }}</h3>
        <div class="field">
          <label>이름 *</label>
          <input v-model="createModal.name" @keyup.enter="submitCreate" autofocus />
        </div>
        <div v-if="createModal.type === 'building'" class="field">
          <label>층수</label>
          <input v-model.number="createModal.floors" type="number" min="1" />
        </div>
        <div class="field" v-if="createModal.type === 'site'">
          <label>설명</label>
          <input v-model="createModal.description" />
        </div>
        <div v-if="createError" class="error">{{ createError }}</div>
        <div class="modal-actions">
          <button @click="submitCreate">추가</button>
          <button class="cancel" @click="createModal = null">취소</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useTopologyStore } from "@/stores/topology";
import api from "@/api/client";

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
}

const rows = computed((): Row[] => {
  const q = search.value.toLowerCase();
  const result: Row[] = [];
  for (const g of topo.groups) {
    if (!q || g.name.toLowerCase().includes(q)) {
      result.push({ type: "group", id: g.id, name: g.name, parentLabel: "—" });
    }
    for (const s of g.sites) {
      if (!q || s.name.toLowerCase().includes(q)) {
        result.push({ type: "site", id: s.id, name: s.name, parentLabel: g.name, parentId: g.id });
      }
      for (const b of s.buildings) {
        if (!q || b.name.toLowerCase().includes(q)) {
          result.push({ type: "building", id: b.id, name: b.name, parentLabel: `${g.name} / ${s.name}`, parentId: s.id });
        }
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

// Inline edit
interface EditTarget { key: string; type: string; id: number; name: string }
const editTarget = ref<EditTarget | null>(null);

function startInlineEdit(row: Row) {
  editTarget.value = { key: `${row.type}-${row.id}`, type: row.type, id: row.id, name: row.name };
}

async function saveInlineEdit() {
  if (!editTarget.value || !editTarget.value.name.trim()) { editTarget.value = null; return; }
  const { type, id, name } = editTarget.value;
  try {
    if (type === "group") await api.patch(`/groups/${id}`, { name });
    else if (type === "site") await api.patch(`/sites/${id}`, { name });
    else await api.patch(`/buildings/${id}`, { name });
    await topo.fetchGroups();
  } finally {
    editTarget.value = null;
  }
}

// Create modal
interface CreateModal { type: "group" | "site" | "building"; title: string; name: string; description: string; floors: number; parentId?: number }
const createModal = ref<CreateModal | null>(null);
const createError = ref("");

function openCreate(type: "group" | "site" | "building", parent?: Row) {
  const titles = { group: "그룹 추가", site: `사이트 추가 — ${parent?.name}`, building: `건물 추가 — ${parent?.name}` };
  createModal.value = { type, title: titles[type], name: "", description: "", floors: 1, parentId: parent?.id };
  createError.value = "";
}

async function submitCreate() {
  if (!createModal.value?.name.trim()) { createError.value = "이름을 입력하세요."; return; }
  try {
    const { type, name, description, floors, parentId } = createModal.value;
    if (type === "group") await topo.createGroup(name, description);
    else if (type === "site") await topo.createSite(parentId!, name, description);
    else await topo.createBuilding(parentId!, name, floors);
    await topo.fetchGroups();
    createModal.value = null;
  } catch (e: any) {
    createError.value = e.response?.data?.detail || "오류가 발생했습니다.";
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
.page { max-width: 900px; }
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
.type-badge { padding: 0.15rem 0.5rem; border-radius: 10px; font-size: 0.78rem; font-weight: 600; }
.type-badge.group { background: #e0e7ff; color: #3730a3; }
.type-badge.site { background: #d1fae5; color: #065f46; }
.type-badge.building { background: #fef3c7; color: #92400e; }
.name-cell { min-width: 180px; }
.name-text { cursor: default; }
.inline-edit { width: 100%; padding: 0.3rem 0.5rem; border: 1px solid #4299e1; border-radius: 4px; font-size: 0.9rem; outline: none; }
.parent-cell { color: #718096; font-size: 0.85rem; }
.row-actions { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.btn-sm { padding: 0.25rem 0.55rem; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.78rem; background: white; white-space: nowrap; }
.btn-sm:hover { background: #f7fafc; }
.btn-sm.danger { border-color: #fed7d7; color: #e53e3e; }
.btn-sm.danger:hover { background: #fff5f5; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal { background: white; border-radius: 10px; padding: 1.75rem; width: 360px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
.modal h3 { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.75rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: #4a5568; }
.field input { padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; outline: none; }
.field input:focus { border-color: #4299e1; }
.error { color: #e53e3e; font-size: 0.85rem; margin-top: 0.25rem; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.25rem; justify-content: flex-end; }
.modal-actions button { padding: 0.45rem 1.1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; background: #4299e1; color: white; font-weight: 500; }
.modal-actions button.cancel { background: #e2e8f0; color: #4a5568; }
</style>
