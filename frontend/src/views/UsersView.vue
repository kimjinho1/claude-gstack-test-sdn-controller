<template>
  <div class="page">
    <div class="page-header">
      <h2>사용자 관리</h2>
      <div class="actions">
        <input v-model="search" class="search" placeholder="사용자명 검색..." />
        <button v-if="selected.size > 0" class="btn-danger" @click="bulkDelete">
          선택 삭제 ({{ selected.size }})
        </button>
        <button class="btn-primary" @click="openCreate">+ 사용자 추가</button>
      </div>
    </div>

    <table class="table">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>사용자명</th>
          <th>역할</th>
          <th>그룹 접근</th>
          <th>상태</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filtered.length === 0">
          <td colspan="5" class="empty">사용자가 없습니다.</td>
        </tr>
        <tr
          v-for="u in filtered"
          :key="u.id"
          class="data-row"
          @click="openEdit(u)"
          @contextmenu.prevent="openCtx($event, u)"
        >
          <td @click.stop><input type="checkbox" :checked="selected.has(u.id)" @change="toggleOne(u.id)" /></td>
          <td><strong>{{ u.username }}</strong></td>
          <td><span class="role-badge" :class="u.role.toLowerCase()">{{ ROLE_LABEL[u.role] }}</span></td>
          <td class="group-access-cell">
            <span v-if="!groupAccessMap[u.id] || groupAccessMap[u.id].length === 0" class="access-all">전체</span>
            <span v-else class="access-count">{{ groupAccessMap[u.id].length }}개 그룹</span>
          </td>
          <td><span :class="u.is_active ? 'status-active' : 'status-inactive'">{{ u.is_active ? "활성" : "비활성" }}</span></td>
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
      <button class="ctx-item danger" @click="confirmDelete(ctxMenu.user); ctxMenu = null">🗑 삭제</button>
    </div>

    <!-- User Drawer -->
    <DrawerPanel v-model="drawerOpen" :title="drawerUser?.id ? '사용자 정보 수정' : '사용자 추가'">
      <div v-if="drawerUser">
        <div class="section-title">기본 정보</div>

        <div class="field">
          <label>사용자명 *</label>
          <input v-model="drawerUser.username" placeholder="username" />
        </div>
        <div class="field">
          <label>비밀번호 {{ drawerUser.id ? "(변경 시 입력)" : "*" }}</label>
          <input v-model="drawerUser.password" type="password" placeholder="비밀번호" />
        </div>
        <div class="field">
          <label>역할 *</label>
          <select v-model="drawerUser.role">
            <option v-for="r in availableRoles" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
          </select>
        </div>
        <div class="field-row">
          <label class="check-label">
            <input type="checkbox" v-model="drawerUser.is_active" />
            활성 계정
          </label>
          <label class="check-label">
            <input type="checkbox" v-model="drawerUser.must_change_password" />
            첫 로그인 시 비밀번호 변경
          </label>
        </div>

        <div class="section-divider" />
        <div class="section-title">그룹 접근 권한</div>
        <p class="section-desc">접근할 수 있는 그룹을 선택하세요. 선택 없으면 모든 그룹에 접근합니다.</p>

        <div class="group-list">
          <label class="group-item all-item">
            <input
              type="checkbox"
              :checked="drawerUser.groupIds.length === 0"
              @change="toggleAllGroups"
            />
            <span class="group-name"><strong>전체 그룹</strong></span>
          </label>
          <label v-for="g in topoStore.groups" :key="g.id" class="group-item">
            <input
              type="checkbox"
              :checked="drawerUser.groupIds.includes(g.id)"
              @change="toggleGroup(g.id)"
            />
            <span class="group-name">{{ g.name }}</span>
            <span class="group-site-count">사이트 {{ g.sites.length }}개</span>
          </label>
        </div>

        <div v-if="drawerError" class="error-msg">{{ drawerError }}</div>
      </div>

      <template #footer>
        <button class="btn-cancel" @click="drawerOpen = false">취소</button>
        <button class="btn-save" @click="submitDrawer" :disabled="drawerLoading">
          {{ drawerLoading ? "저장 중..." : (drawerUser?.id ? "저장" : "추가") }}
        </button>
      </template>
    </DrawerPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useAuthStore, ROLE_LABEL, ROLE_LEVEL, type UserRole } from "@/stores/auth";
import { useUserManageStore, type ManagedUser } from "@/stores/userManage";
import { useTopologyStore } from "@/stores/topology";
import api from "@/api/client";
import DrawerPanel from "@/components/DrawerPanel.vue";

const auth = useAuthStore();
const store = useUserManageStore();
const topoStore = useTopologyStore();

const search = ref("");
const selected = ref(new Set<number>());

// group access map: user_id → group_id[]
const groupAccessMap = ref<Record<number, number[]>>({});

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return store.users.filter((u) => u.username.toLowerCase().includes(q));
});

const allSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every((u) => selected.value.has(u.id))
);

function toggleAll(e: Event) {
  if ((e.target as HTMLInputElement).checked) filtered.value.forEach((u) => selected.value.add(u.id));
  else selected.value.clear();
}
function toggleOne(id: number) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id);
}

// Context menu
interface CtxMenu { x: number; y: number; user: ManagedUser }
const ctxMenu = ref<CtxMenu | null>(null);

function openCtx(e: MouseEvent, u: ManagedUser) {
  ctxMenu.value = { x: e.clientX, y: e.clientY, user: u };
}
function closeCtx() { ctxMenu.value = null; }

onMounted(() => document.addEventListener("click", closeCtx));
onUnmounted(() => document.removeEventListener("click", closeCtx));

// Roles available to current user
const availableRoles = computed((): UserRole[] =>
  (["SUPERADMIN", "ADMIN", "USER", "GUEST"] as UserRole[]).filter(
    (r) => ROLE_LEVEL[r] < auth.roleLevel
  )
);

// Drawer state
interface DrawerState {
  id: number | null;
  username: string;
  password: string;
  role: UserRole;
  is_active: boolean;
  must_change_password: boolean;
  groupIds: number[];
}

const drawerOpen = ref(false);
const drawerUser = ref<DrawerState | null>(null);
const drawerError = ref("");
const drawerLoading = ref(false);

function openCreate() {
  drawerUser.value = {
    id: null, username: "", password: "",
    role: availableRoles.value[0] ?? "GUEST",
    is_active: true, must_change_password: false,
    groupIds: [],
  };
  drawerError.value = "";
  drawerOpen.value = true;
}

async function openEdit(u: ManagedUser) {
  // fetch group access
  let groupIds: number[] = [];
  try {
    const { data } = await api.get(`/users/${u.id}/groups`);
    groupIds = data.group_ids;
  } catch { /* ignore */ }
  groupAccessMap.value[u.id] = groupIds;

  drawerUser.value = {
    id: u.id, username: u.username, password: "",
    role: u.role, is_active: u.is_active, must_change_password: u.must_change_password,
    groupIds,
  };
  drawerError.value = "";
  drawerOpen.value = true;
}

function toggleAllGroups(e: Event) {
  if (!drawerUser.value) return;
  drawerUser.value.groupIds = (e.target as HTMLInputElement).checked ? [] : [...topoStore.groups.map((g) => g.id)];
}

function toggleGroup(id: number) {
  if (!drawerUser.value) return;
  const idx = drawerUser.value.groupIds.indexOf(id);
  if (idx >= 0) drawerUser.value.groupIds.splice(idx, 1);
  else drawerUser.value.groupIds.push(id);
}

async function submitDrawer() {
  if (!drawerUser.value) return;
  if (!drawerUser.value.username) { drawerError.value = "사용자명을 입력하세요."; return; }
  if (!drawerUser.value.id && !drawerUser.value.password) { drawerError.value = "비밀번호를 입력하세요."; return; }

  drawerLoading.value = true;
  drawerError.value = "";
  try {
    let userId = drawerUser.value.id;
    if (userId) {
      const payload: Record<string, unknown> = {
        username: drawerUser.value.username,
        role: drawerUser.value.role,
        is_active: drawerUser.value.is_active,
        must_change_password: drawerUser.value.must_change_password,
      };
      if (drawerUser.value.password) payload.password = drawerUser.value.password;
      await store.updateUser(userId, payload as any);
    } else {
      const created = await store.createUser({
        username: drawerUser.value.username,
        password: drawerUser.value.password,
        role: drawerUser.value.role,
        must_change_password: drawerUser.value.must_change_password,
      });
      userId = created.id;
    }
    // Save group access
    await api.put(`/users/${userId}/groups`, { ids: drawerUser.value.groupIds });
    groupAccessMap.value[userId!] = [...drawerUser.value.groupIds];

    drawerOpen.value = false;
  } catch (e: any) {
    drawerError.value = e.response?.data?.detail || "오류가 발생했습니다.";
  } finally {
    drawerLoading.value = false;
  }
}

async function confirmDelete(u: ManagedUser) {
  if (!confirm(`"${u.username}" 계정을 삭제하시겠습니까?`)) return;
  await store.deleteUser(u.id);
  delete groupAccessMap.value[u.id];
}

async function bulkDelete() {
  if (!confirm(`선택한 ${selected.value.size}개 계정을 삭제하시겠습니까?`)) return;
  await store.bulkDelete([...selected.value]);
  selected.value.clear();
}

onMounted(async () => {
  await store.fetchUsers();
  await topoStore.fetchGroups();
  // preload group access for all users
  for (const u of store.users) {
    try {
      const { data } = await api.get(`/users/${u.id}/groups`);
      groupAccessMap.value[u.id] = data.group_ids;
    } catch { /* ignore */ }
  }
});
</script>

<style scoped>
.page { max-width: 860px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.page-header h2 { font-size: 1.15rem; font-weight: 700; }
.actions { display: flex; gap: 0.6rem; align-items: center; }
.search { padding: 0.45rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; width: 200px; outline: none; }
.search:focus { border-color: #4299e1; }
.btn-primary { padding: 0.45rem 1rem; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-danger { padding: 0.45rem 1rem; background: #e53e3e; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }

.table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.table th { background: #f7fafc; padding: 0.75rem 1rem; text-align: left; font-size: 0.82rem; color: #4a5568; font-weight: 600; border-bottom: 1px solid #e2e8f0; }
.table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f0f4f8; font-size: 0.9rem; }
.table tr:last-child td { border-bottom: none; }
.empty { text-align: center; color: #a0aec0; padding: 2rem !important; }
.data-row { cursor: pointer; transition: background 0.1s; }
.data-row:hover td { background: #f7fafc; }

.role-badge { padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.role-badge.superadmin { background: #fef3c7; color: #92400e; }
.role-badge.admin { background: #dbeafe; color: #1e40af; }
.role-badge.user { background: #d1fae5; color: #065f46; }
.role-badge.guest { background: #f3f4f6; color: #6b7280; }

.access-all { color: #a0aec0; font-size: 0.83rem; }
.access-count { color: #4299e1; font-size: 0.83rem; font-weight: 500; }
.status-active { color: #059669; font-size: 0.85rem; }
.status-inactive { color: #dc2626; font-size: 0.85rem; }

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
.section-title { font-size: 0.78rem; font-weight: 700; color: #718096; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
.section-divider { border: none; border-top: 1px solid #e2e8f0; margin: 1.25rem 0; }
.section-desc { font-size: 0.83rem; color: #718096; margin-bottom: 0.75rem; }

.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.75rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: #4a5568; }
.field input, .field select { padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; outline: none; }
.field input:focus, .field select:focus { border-color: #4299e1; }
.field-row { display: flex; gap: 1.5rem; margin-bottom: 0.75rem; }
.check-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: #4a5568; cursor: pointer; }

.group-list { display: flex; flex-direction: column; gap: 0.3rem; max-height: 280px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.5rem; }
.group-item { display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0.6rem; border-radius: 6px; cursor: pointer; }
.group-item:hover { background: #f7fafc; }
.all-item { border-bottom: 1px solid #e2e8f0; margin-bottom: 0.3rem; padding-bottom: 0.6rem; }
.group-name { flex: 1; font-size: 0.88rem; }
.group-site-count { font-size: 0.78rem; color: #a0aec0; }

.error-msg { color: #e53e3e; font-size: 0.85rem; margin-top: 0.75rem; }

/* Footer buttons */
.btn-save { padding: 0.5rem 1.25rem; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-save:hover { background: #3182ce; }
.btn-save:disabled { background: #a0aec0; cursor: not-allowed; }
.btn-cancel { padding: 0.5rem 1.25rem; background: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.btn-cancel:hover { background: #cbd5e0; }
</style>
