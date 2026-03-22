<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <h3>장비 등록</h3>

      <form @submit.prevent="handleSubmit">
        <div class="grid-2">
          <div class="field">
            <label>장비명 *</label>
            <input v-model="form.name" placeholder="SW-01" required />
          </div>
          <div class="field">
            <label>IP 주소 *</label>
            <input v-model="form.ip_addr" placeholder="10.0.1.1" required />
          </div>
          <div class="field">
            <label>MAC 주소 *</label>
            <input
              :value="form.mac_addr"
              @input="onMacInput"
              placeholder="00:1A:2B:3C:4D:5E"
              maxlength="17"
              required
            />
          </div>
          <div class="field">
            <label>프로토콜 *</label>
            <select v-model="form.protocol">
              <option value="SSH">SSH</option>
              <option value="REST">REST (Phase 2)</option>
            </select>
          </div>
          <div class="field">
            <label>그룹/사이트 *</label>
            <select v-model="form.site_id" required>
              <option value="" disabled>사이트 선택</option>
              <template v-for="g in groups" :key="g.id">
                <optgroup :label="g.name">
                  <option v-for="s in g.sites" :key="s.id" :value="s.id">{{ s.name }}</option>
                </optgroup>
              </template>
            </select>
          </div>
          <div class="field">
            <label>건물 *</label>
            <select v-model="form.building_id" required :disabled="!form.site_id">
              <option value="" disabled>건물 선택</option>
              <option v-for="b in availableBuildings" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <div class="field">
            <label>층</label>
            <input v-model.number="form.floor" type="number" placeholder="예: 3" min="1" />
          </div>
        </div>

        <!-- SSH fields -->
        <template v-if="form.protocol === 'SSH'">
          <div class="section-title">SSH 연동 정보</div>
          <div class="grid-3">
            <div class="field">
              <label>SSH ID *</label>
              <input v-model="form.ssh_id" placeholder="admin" required />
            </div>
            <div class="field">
              <label>SSH 비밀번호 *</label>
              <input v-model="form.ssh_password" type="password" required />
            </div>
            <div class="field">
              <label>SSH 포트</label>
              <input v-model.number="form.ssh_port" type="number" placeholder="22" />
            </div>
          </div>
        </template>

        <!-- REST fields -->
        <template v-else>
          <div class="section-title">REST 연동 정보 <span class="note">(Phase 2 — 등록만 가능, 연동 미지원)</span></div>
          <div class="grid-3">
            <div class="field">
              <label>REST ID *</label>
              <input v-model="form.rest_id" placeholder="admin" required />
            </div>
            <div class="field">
              <label>REST 비밀번호 *</label>
              <input v-model="form.rest_password" type="password" required />
            </div>
            <div class="field">
              <label>REST 포트 *</label>
              <input v-model.number="form.rest_port" type="number" placeholder="8080" required />
            </div>
          </div>
        </template>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="modal-actions">
          <button type="submit" :disabled="loading">{{ loading ? "등록 중..." : "등록" }}</button>
          <button type="button" class="cancel" @click="emit('close')">취소</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from "vue";
import { useTopologyStore } from "@/stores/topology";
import { useDeviceStore } from "@/stores/device";

const emit = defineEmits(["close", "created"]);

const topologyStore = useTopologyStore();
const deviceStore = useDeviceStore();

const groups = computed(() => topologyStore.groups);
const error = ref("");
const loading = ref(false);

const form = reactive({
  name: "", ip_addr: "", mac_addr: "",
  protocol: "SSH",
  site_id: "" as number | "",
  building_id: "" as number | "",
  floor: undefined as number | undefined,
  ssh_id: "", ssh_password: "", ssh_port: 22,
  rest_id: "", rest_password: "", rest_port: undefined as number | undefined,
});

function onMacInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.replace(/[^0-9a-fA-F]/g, "");
  const trimmed = raw.slice(0, 12);
  const formatted = trimmed.match(/.{1,2}/g)?.join(":").toUpperCase() ?? "";
  form.mac_addr = formatted;
  // keep cursor at end
  const input = e.target as HTMLInputElement;
  requestAnimationFrame(() => { input.value = formatted; });
}

const availableBuildings = computed(() => {
  if (!form.site_id) return [];
  for (const g of groups.value) {
    const site = g.sites.find((s) => s.id === form.site_id);
    if (site) return site.buildings;
  }
  return [];
});

async function handleSubmit() {
  error.value = "";
  loading.value = true;
  try {
    const payload: Record<string, unknown> = {
      name: form.name, ip_addr: form.ip_addr, mac_addr: form.mac_addr,
      protocol: form.protocol,
      site_id: form.site_id, building_id: form.building_id,
      floor: form.floor,
    };
    if (form.protocol === "SSH") {
      payload.ssh_id = form.ssh_id;
      payload.ssh_password = form.ssh_password;
      payload.ssh_port = form.ssh_port;
    } else {
      payload.rest_id = form.rest_id;
      payload.rest_password = form.rest_password;
      payload.rest_port = form.rest_port;
    }
    await deviceStore.createDevice(payload);
    emit("created");
  } catch (e: any) {
    error.value = e.response?.data?.detail || "등록에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 300; }
.modal { background: white; border-radius: 10px; padding: 1.75rem; width: 560px; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 1.25rem; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field label { font-size: 0.82rem; font-weight: 500; color: #4a5568; }
.field input, .field select { padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.9rem; outline: none; }
.field input:focus, .field select:focus { border-color: #4299e1; }
.section-title { font-size: 0.85rem; font-weight: 600; color: #4a5568; margin: 1rem 0 0.5rem; border-top: 1px solid #f0f4f8; padding-top: 0.75rem; }
.note { font-weight: 400; color: #e53e3e; font-size: 0.78rem; }
.error { color: #e53e3e; font-size: 0.85rem; margin-top: 0.75rem; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.25rem; justify-content: flex-end; }
.modal-actions button { padding: 0.5rem 1.25rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; background: #4299e1; color: white; font-weight: 500; }
.modal-actions button:disabled { background: #a0aec0; cursor: not-allowed; }
.modal-actions button.cancel { background: #e2e8f0; color: #4a5568; }
</style>
