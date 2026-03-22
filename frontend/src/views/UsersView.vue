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
          <th>상태</th>
          <th>비밀번호 변경</th>
          <th>작업</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filtered.length === 0">
          <td colspan="6" class="empty">사용자가 없습니다.</td>
        </tr>
        <tr v-for="u in filtered" :key="u.id">
          <td><input type="checkbox" :checked="selected.has(u.id)" @change="toggleOne(u.id)" /></td>
          <td>{{ u.username }}</td>
          <td><span class="role-badge" :class="u.role.toLowerCase()">{{ ROLE_LABEL[u.role] }}</span></td>
          <td><span :class="u.is_active ? 'active' : 'inactive'">{{ u.is_active ? "활성" : "비활성" }}</span></td>
          <td>{{ u.must_change_password ? "필요" : "—" }}</td>
          <td class="row-actions">
            <button class="btn-sm" @click="openEdit(u)">수정</button>
            <button class="btn-sm danger" @click="confirmDelete(u)">삭제</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create/Edit Modal -->
    <div v-if="modal" class="modal-overlay" @click.self="modal = null">
      <div class="modal">
        <h3>{{ modal.id ? "사용자 수정" : "사용자 추가" }}</h3>
        <div class="field">
          <label>사용자명 *</label>
          <input v-model="modal.username" placeholder="username" />
        </div>
        <div class="field">
          <label>비밀번호 {{ modal.id ? "(변경 시 입력)" : "*" }}</label>
          <input v-model="modal.password" type="password" placeholder="비밀번호" />
        </div>
        <div class="field">
          <label>역할 *</label>
          <select v-model="modal.role">
            <option v-for="r in availableRoles" :key="r" :value="r">{{ ROLE_LABEL[r] }}</option>
          </select>
        </div>
        <div class="field row">
          <label><input type="checkbox" v-model="modal.is_active" /> 활성 계정</label>
          <label><input type="checkbox" v-model="modal.must_change_password" /> 첫 로그인 시 비밀번호 변경 강제</label>
        </div>
        <div v-if="modalError" class="error">{{ modalError }}</div>
        <div class="modal-actions">
          <button @click="submitModal" :disabled="modalLoading">{{ modal.id ? "저장" : "추가" }}</button>
          <button class="cancel" @click="modal = null">취소</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAuthStore, ROLE_LABEL, ROLE_LEVEL, type UserRole } from "@/stores/auth";
import { useUserManageStore, type ManagedUser } from "@/stores/userManage";

const auth = useAuthStore();
const store = useUserManageStore();

const search = ref("");
const selected = ref(new Set<number>());

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

// Roles that current user can assign (strictly lower level)
const availableRoles = computed((): UserRole[] =>
  (["SUPERADMIN", "ADMIN", "USER", "GUEST"] as UserRole[]).filter(
    (r) => ROLE_LEVEL[r] < auth.roleLevel
  )
);

interface ModalState {
  id: number | null;
  username: string;
  password: string;
  role: UserRole;
  is_active: boolean;
  must_change_password: boolean;
}

const modal = ref<ModalState | null>(null);
const modalError = ref("");
const modalLoading = ref(false);

function openCreate() {
  modal.value = {
    id: null, username: "", password: "",
    role: availableRoles.value[0] ?? "GUEST",
    is_active: true, must_change_password: false,
  };
  modalError.value = "";
}

function openEdit(u: ManagedUser) {
  modal.value = {
    id: u.id, username: u.username, password: "",
    role: u.role, is_active: u.is_active, must_change_password: u.must_change_password,
  };
  modalError.value = "";
}

async function submitModal() {
  if (!modal.value) return;
  if (!modal.value.username) { modalError.value = "사용자명을 입력하세요."; return; }
  if (!modal.value.id && !modal.value.password) { modalError.value = "비밀번호를 입력하세요."; return; }
  modalLoading.value = true;
  modalError.value = "";
  try {
    if (modal.value.id) {
      const payload: Record<string, unknown> = {
        username: modal.value.username,
        role: modal.value.role,
        is_active: modal.value.is_active,
        must_change_password: modal.value.must_change_password,
      };
      if (modal.value.password) payload.password = modal.value.password;
      await store.updateUser(modal.value.id, payload as any);
    } else {
      await store.createUser({
        username: modal.value.username,
        password: modal.value.password,
        role: modal.value.role,
        must_change_password: modal.value.must_change_password,
      });
    }
    modal.value = null;
  } catch (e: any) {
    modalError.value = e.response?.data?.detail || "오류가 발생했습니다.";
  } finally {
    modalLoading.value = false;
  }
}

async function confirmDelete(u: ManagedUser) {
  if (!confirm(`"${u.username}" 계정을 삭제하시겠습니까?`)) return;
  await store.deleteUser(u.id);
}

async function bulkDelete() {
  if (!confirm(`선택한 ${selected.value.size}개 계정을 삭제하시겠습니까?`)) return;
  await store.bulkDelete([...selected.value]);
  selected.value.clear();
}

onMounted(() => store.fetchUsers());
</script>

<style scoped>
.page { max-width: 900px; }
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
.role-badge { padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
.role-badge.superadmin { background: #fef3c7; color: #92400e; }
.role-badge.admin { background: #dbeafe; color: #1e40af; }
.role-badge.user { background: #d1fae5; color: #065f46; }
.role-badge.guest { background: #f3f4f6; color: #6b7280; }
.active { color: #059669; font-size: 0.85rem; }
.inactive { color: #dc2626; font-size: 0.85rem; }
.row-actions { display: flex; gap: 0.4rem; }
.btn-sm { padding: 0.25rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.8rem; background: white; }
.btn-sm:hover { background: #f7fafc; }
.btn-sm.danger { border-color: #fed7d7; color: #e53e3e; }
.btn-sm.danger:hover { background: #fff5f5; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal { background: white; border-radius: 10px; padding: 1.75rem; width: 400px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
.modal h3 { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.75rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: #4a5568; }
.field input, .field select { padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; outline: none; }
.field input:focus, .field select:focus { border-color: #4299e1; }
.field.row { flex-direction: row; gap: 1.5rem; }
.field.row label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; }
.error { color: #e53e3e; font-size: 0.85rem; margin-top: 0.5rem; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.25rem; justify-content: flex-end; }
.modal-actions button { padding: 0.45rem 1.1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; background: #4299e1; color: white; font-weight: 500; }
.modal-actions button:disabled { background: #a0aec0; cursor: not-allowed; }
.modal-actions button.cancel { background: #e2e8f0; color: #4a5568; }
</style>
