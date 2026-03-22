<template>
  <div class="settings-wrap">
    <div class="page-header">
      <h2>컨트롤러 설정</h2>
    </div>

    <!-- Sub-tab nav -->
    <div class="sub-tabs">
      <button
        class="sub-tab"
        :class="{ active: activeTab === 'models' }"
        @click="activeTab = 'models'"
      >장비 모델</button>
      <button
        class="sub-tab"
        :class="{ active: activeTab === 'virtual' }"
        @click="switchToVirtual"
      >가상 장비</button>
    </div>

    <!-- ── 장비 모델 탭 ───────────────────────────────────────────────── -->
    <div v-if="activeTab === 'models'" class="tab-content">
      <div class="toolbar">
        <button class="btn-primary" @click="openCreateModel">+ 모델 추가</button>
      </div>

      <div v-if="modelLoading" class="empty-msg">불러오는 중...</div>
      <div v-else-if="store.deviceModels.length === 0" class="empty-msg">등록된 장비 모델이 없습니다.</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>이름</th>
            <th>벤더</th>
            <th>장비 타입</th>
            <th>Docker 이미지</th>
            <th>가상</th>
            <th>설명</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in store.deviceModels" :key="m.id">
            <td class="name-cell">
              <img v-if="m.image_url" :src="m.image_url" class="model-icon" alt="" />
              <span>{{ m.name }}</span>
            </td>
            <td>{{ m.vendor }}</td>
            <td><code>{{ m.device_type }}</code></td>
            <td><code>{{ m.docker_image || '—' }}</code></td>
            <td>{{ m.is_virtual ? '✓' : '' }}</td>
            <td class="desc-cell">{{ m.description || '—' }}</td>
            <td class="action-cell">
              <button class="btn-icon" @click="openEditModel(m)" title="수정">✏️</button>
              <button class="btn-icon danger" @click="confirmDeleteModel(m)" title="삭제">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── 가상 장비 탭 ───────────────────────────────────────────────── -->
    <div v-if="activeTab === 'virtual'" class="tab-content">
      <div class="toolbar">
        <button class="btn-primary" @click="openLaunchModal">+ 가상 장비 실행</button>
        <button class="btn-secondary" @click="refreshVirtual">새로고침</button>
      </div>

      <div v-if="virtualLoading" class="empty-msg">불러오는 중...</div>
      <div v-else-if="store.virtualDevices.length === 0" class="empty-msg">
        실행 중인 가상 장비가 없습니다.<br />
        <span class="hint">Docker에서 ceos:latest 이미지를 먼저 로드해야 합니다.</span>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>이름</th>
            <th>모델</th>
            <th>컨테이너 IP (장비 등록용)</th>
            <th>호스트 포트</th>
            <th>상태</th>
            <th>컨테이너 ID</th>
            <th>생성 시각</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in store.virtualDevices" :key="v.id">
            <td>{{ v.name }}</td>
            <td>{{ modelName(v.model_id) }}</td>
            <td>
              <span v-if="v.container_ip" class="ip-hint">
                <code>{{ v.container_ip }}</code>
                <span class="ip-note">SSH 포트: 22</span>
              </span>
              <span v-else class="txt-muted">—</span>
            </td>
            <td>{{ v.ssh_port }}</td>
            <td>
              <span class="status-badge" :class="v.status">{{ statusLabel(v.status) }}</span>
            </td>
            <td><code>{{ v.container_id ? v.container_id.slice(0, 12) : '—' }}</code></td>
            <td>{{ formatDate(v.created_at) }}</td>
            <td class="action-cell">
              <button
                v-if="v.status === 'running' || v.status === 'starting'"
                class="btn-icon danger"
                @click="stopVdev(v)"
                title="중지"
              >⏹</button>
              <button class="btn-icon danger" @click="deleteVdev(v)" title="삭제">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="reg-hint">
        💡 장비 등록 시 <strong>컨테이너 IP</strong>와 <strong>SSH 포트 22</strong>를 사용하세요.
        (호스트 포트는 외부 접속용이며 폴러가 직접 연결하지 않습니다.)
      </p>
    </div>

    <!-- ── 모델 추가/수정 모달 ──────────────────────────────────────── -->
    <div v-if="modelModal.open" class="modal-overlay" @click.self="closeModelModal">
      <div class="modal">
        <h3>{{ modelModal.editing ? '장비 모델 수정' : '장비 모델 추가' }}</h3>
        <form @submit.prevent="submitModel">
          <div class="grid-2">
            <div class="field">
              <label>이름 *</label>
              <input v-model="modelModal.form.name" required placeholder="cEOS-lab" />
            </div>
            <div class="field">
              <label>벤더 *</label>
              <input v-model="modelModal.form.vendor" required placeholder="Arista" />
            </div>
            <div class="field">
              <label>장비 타입 *</label>
              <select v-model="modelModal.form.device_type" required>
                <option value="cisco_ios">Cisco IOS</option>
                <option value="cisco_xe">Cisco IOS-XE</option>
                <option value="cisco_nxos">Cisco NX-OS</option>
                <option value="arista_eos">Arista EOS</option>
              </select>
            </div>
            <div class="field">
              <label>Docker 이미지</label>
              <input v-model="modelModal.form.docker_image" placeholder="ceos:latest" />
            </div>
            <div class="field">
              <label>아이콘 URL</label>
              <input v-model="modelModal.form.image_url" placeholder="https://..." />
            </div>
            <div class="field checkbox-field">
              <label>
                <input type="checkbox" v-model="modelModal.form.is_virtual" />
                가상 장비
              </label>
            </div>
          </div>
          <div class="field full-width">
            <label>설명</label>
            <input v-model="modelModal.form.description" placeholder="간단한 설명" />
          </div>
          <div v-if="modelModal.error" class="error">{{ modelModal.error }}</div>
          <div class="modal-actions">
            <button type="submit" :disabled="modelModal.loading">
              {{ modelModal.loading ? '저장 중...' : '저장' }}
            </button>
            <button type="button" class="cancel" @click="closeModelModal">취소</button>
          </div>
        </form>
      </div>
    </div>

    <!-- ── 가상 장비 실행 모달 ──────────────────────────────────────── -->
    <div v-if="launchModal.open" class="modal-overlay" @click.self="launchModal.open = false">
      <div class="modal">
        <h3>가상 장비 실행</h3>
        <form @submit.prevent="submitLaunch">
          <div class="field">
            <label>장비 이름 *</label>
            <input v-model="launchModal.form.name" required placeholder="arista-lab-01" />
          </div>
          <div class="field">
            <label>장비 모델 *</label>
            <select v-model="launchModal.form.model_id" required>
              <option value="" disabled>모델 선택</option>
              <option
                v-for="m in virtualModels"
                :key="m.id"
                :value="m.id"
              >{{ m.name }} ({{ m.vendor }})</option>
            </select>
          </div>
          <div class="field">
            <label>SSH 호스트 포트 *</label>
            <input v-model.number="launchModal.form.ssh_port" type="number" required placeholder="2222" min="1024" max="65535" />
          </div>
          <p class="launch-note">
            컨테이너가 실행되면 <code>ssh admin@localhost -p {{ launchModal.form.ssh_port }}</code>로 접속할 수 있습니다.<br/>
            ceos:latest 이미지가 사전에 로드되어 있어야 합니다.
          </p>
          <div v-if="launchModal.error" class="error">{{ launchModal.error }}</div>
          <div class="modal-actions">
            <button type="submit" :disabled="launchModal.loading">
              {{ launchModal.loading ? '실행 중...' : '실행' }}
            </button>
            <button type="button" class="cancel" @click="launchModal.open = false">취소</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useControllerStore, type DeviceModel, type VirtualDevice } from "@/stores/controller";

const store = useControllerStore();
const activeTab = ref<"models" | "virtual">("models");
const modelLoading = ref(false);
const virtualLoading = ref(false);

onMounted(async () => {
  modelLoading.value = true;
  await store.fetchDeviceModels().finally(() => (modelLoading.value = false));
});

async function switchToVirtual() {
  activeTab.value = "virtual";
  await refreshVirtual();
}

async function refreshVirtual() {
  virtualLoading.value = true;
  await store.fetchVirtualDevices().finally(() => (virtualLoading.value = false));
}

// ── Model modal ─────────────────────────────────────────────────────────────

const modelModal = reactive({
  open: false,
  editing: null as DeviceModel | null,
  loading: false,
  error: "",
  form: {
    name: "", vendor: "", device_type: "arista_eos",
    docker_image: "", image_url: "", description: "", is_virtual: false,
  },
});

function openCreateModel() {
  modelModal.editing = null;
  modelModal.form = { name: "", vendor: "", device_type: "arista_eos", docker_image: "", image_url: "", description: "", is_virtual: false };
  modelModal.error = "";
  modelModal.open = true;
}

function openEditModel(m: DeviceModel) {
  modelModal.editing = m;
  modelModal.form = {
    name: m.name, vendor: m.vendor, device_type: m.device_type,
    docker_image: m.docker_image || "", image_url: m.image_url || "",
    description: m.description || "", is_virtual: m.is_virtual,
  };
  modelModal.error = "";
  modelModal.open = true;
}

function closeModelModal() { modelModal.open = false; }

async function submitModel() {
  modelModal.error = "";
  modelModal.loading = true;
  try {
    const payload = {
      ...modelModal.form,
      docker_image: modelModal.form.docker_image || null,
      image_url: modelModal.form.image_url || null,
      description: modelModal.form.description || null,
    };
    if (modelModal.editing) {
      await store.updateDeviceModel(modelModal.editing.id, payload);
    } else {
      await store.createDeviceModel(payload);
    }
    modelModal.open = false;
  } catch (e: any) {
    modelModal.error = e.response?.data?.detail || "저장에 실패했습니다.";
  } finally {
    modelModal.loading = false;
  }
}

async function confirmDeleteModel(m: DeviceModel) {
  if (!confirm(`"${m.name}" 모델을 삭제하시겠습니까?`)) return;
  try {
    await store.deleteDeviceModel(m.id);
  } catch (e: any) {
    alert(e.response?.data?.detail || "삭제에 실패했습니다.");
  }
}

// ── Virtual devices ──────────────────────────────────────────────────────────

const virtualModels = computed(() => store.deviceModels.filter((m) => m.is_virtual && m.docker_image));

const launchModal = reactive({
  open: false,
  loading: false,
  error: "",
  form: { name: "", model_id: "" as number | "", ssh_port: 2222 },
});

function openLaunchModal() {
  if (virtualModels.value.length === 0) {
    alert("Docker 이미지가 설정된 가상 장비 모델이 없습니다. 먼저 장비 모델을 추가하세요.");
    activeTab.value = "models";
    return;
  }
  launchModal.form = { name: "", model_id: virtualModels.value[0]?.id ?? "", ssh_port: 2222 };
  launchModal.error = "";
  launchModal.open = true;

  // Load virtual devices if not loaded
  if (store.virtualDevices.length === 0) refreshVirtual();
}

async function submitLaunch() {
  launchModal.error = "";
  launchModal.loading = true;
  try {
    await store.launchVirtualDevice({
      name: launchModal.form.name,
      model_id: launchModal.form.model_id as number,
      ssh_port: launchModal.form.ssh_port,
    });
    launchModal.open = false;
    activeTab.value = "virtual";
    await refreshVirtual();
  } catch (e: any) {
    launchModal.error = e.response?.data?.detail || "실행에 실패했습니다.";
  } finally {
    launchModal.loading = false;
  }
}

async function stopVdev(v: VirtualDevice) {
  if (!confirm(`"${v.name}" 컨테이너를 중지하시겠습니까?`)) return;
  try {
    await store.stopVirtualDevice(v.id);
  } catch (e: any) {
    alert(e.response?.data?.detail || "중지에 실패했습니다.");
  }
}

async function deleteVdev(v: VirtualDevice) {
  if (!confirm(`"${v.name}"을(를) 삭제하시겠습니까? 실행 중이면 컨테이너도 제거됩니다.`)) return;
  try {
    await store.deleteVirtualDevice(v.id);
  } catch (e: any) {
    alert(e.response?.data?.detail || "삭제에 실패했습니다.");
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function modelName(id: number) {
  return store.deviceModels.find((m) => m.id === id)?.name ?? `모델 #${id}`;
}

function statusLabel(s: string) {
  return { starting: "시작 중", running: "실행 중", stopped: "중지됨", error: "오류" }[s] ?? s;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" });
}
</script>

<style scoped>
.settings-wrap { max-width: 1000px; }

.page-header { margin-bottom: 1.25rem; }
.page-header h2 { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0; }

/* Sub-tabs */
.sub-tabs {
  display: flex; gap: 0; margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--border-color);
}
.sub-tab {
  padding: 0.5rem 1.2rem; background: none; border: none;
  cursor: pointer; font-size: 0.88rem; font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color 0.12s, border-color 0.12s;
}
.sub-tab:hover { color: var(--text-primary); }
.sub-tab.active { color: var(--accent-primary); border-bottom-color: var(--accent-primary); font-weight: 600; }

/* Toolbar */
.toolbar { display: flex; gap: 0.5rem; margin-bottom: 1rem; align-items: center; }
.btn-primary {
  padding: 0.4rem 1rem; background: var(--accent-primary); color: white;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.88rem; font-weight: 500;
}
.btn-primary:hover { background: var(--accent-hover); }
.btn-secondary {
  padding: 0.4rem 0.9rem; background: var(--bg-elevated); color: var(--text-secondary);
  border: 1px solid var(--border-input); border-radius: 6px; cursor: pointer; font-size: 0.88rem;
}
.btn-secondary:hover { color: var(--text-primary); }

/* Table */
.data-table {
  width: 100%; border-collapse: collapse; font-size: 0.88rem;
  background: var(--bg-surface); border-radius: 8px; overflow: hidden;
  border: 1px solid var(--border-subtle);
}
.data-table th {
  padding: 0.55rem 0.75rem; font-size: 0.78rem; font-weight: 600;
  color: var(--text-secondary); background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-color); text-align: left; white-space: nowrap;
}
.data-table td {
  padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary); vertical-align: middle;
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: var(--bg-table-hover); }

.name-cell { display: flex; align-items: center; gap: 0.5rem; }
.model-icon { width: 20px; height: 20px; object-fit: contain; border-radius: 3px; }
.desc-cell { color: var(--text-secondary); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.action-cell { white-space: nowrap; }

code { font-size: 0.8rem; background: var(--bg-elevated); padding: 0.1rem 0.35rem; border-radius: 3px; color: var(--accent-primary); }

.btn-icon {
  background: none; border: none; cursor: pointer; font-size: 0.88rem;
  padding: 0.2rem 0.35rem; border-radius: 4px; opacity: 0.65; transition: opacity 0.12s;
}
.btn-icon:hover { opacity: 1; }
.btn-icon.danger:hover { color: var(--danger); }

/* Status badge */
.status-badge {
  display: inline-block; padding: 0.15rem 0.55rem; border-radius: 10px;
  font-size: 0.75rem; font-weight: 600;
}
.status-badge.running { background: color-mix(in srgb, var(--success) 15%, transparent); color: var(--success); }
.status-badge.starting { background: color-mix(in srgb, var(--warning) 15%, transparent); color: var(--warning); }
.status-badge.stopped { background: var(--bg-elevated); color: var(--text-muted); }
.status-badge.error { background: var(--danger-bg); color: var(--danger); }

.empty-msg { color: var(--text-secondary); text-align: center; padding: 2.5rem 0; }
.hint { font-size: 0.82rem; opacity: 0.7; }
.txt-muted { color: var(--text-muted); }

.ip-hint { display: flex; align-items: center; gap: 0.4rem; }
.ip-note { font-size: 0.75rem; color: var(--text-muted); }

.reg-hint {
  margin-top: 0.75rem; font-size: 0.82rem; color: var(--text-secondary);
  padding: 0.6rem 0.75rem; background: var(--bg-elevated);
  border: 1px solid var(--border-subtle); border-radius: 6px; line-height: 1.5;
}

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal { background: var(--bg-modal); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 1.75rem; width: 520px; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.4); }
h3 { font-size: 1.05rem; font-weight: 700; margin-bottom: 1.25rem; color: var(--text-primary); }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field.full-width { margin-bottom: 0.75rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: var(--text-secondary); }
.field input, .field select { padding: 0.5rem 0.7rem; border: 1px solid var(--border-input); border-radius: 6px; font-size: 0.9rem; outline: none; background: var(--bg-input); color: var(--text-primary); }
.field input:focus, .field select:focus { border-color: var(--accent-primary); }
.checkbox-field { justify-content: flex-end; padding-bottom: 0.25rem; }
.checkbox-field label { flex-direction: row; align-items: center; gap: 0.4rem; font-size: 0.88rem; cursor: pointer; }
.checkbox-field input[type="checkbox"] { width: 14px; height: 14px; cursor: pointer; }

.error { color: var(--danger); font-size: 0.85rem; margin-top: 0.75rem; }

.launch-note { font-size: 0.82rem; color: var(--text-secondary); margin: 0.75rem 0; line-height: 1.55; }

.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.25rem; justify-content: flex-end; }
.modal-actions button { padding: 0.5rem 1.25rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; background: var(--accent-primary); color: white; font-weight: 500; }
.modal-actions button:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-actions button.cancel { background: var(--bg-elevated); color: var(--text-secondary); border: 1px solid var(--border-input); }
.modal-actions button.cancel:hover { background: var(--bg-table-hover); color: var(--text-primary); }
</style>
