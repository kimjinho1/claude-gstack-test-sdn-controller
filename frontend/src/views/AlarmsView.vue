<template>
  <div>
    <div class="page-header">
      <h2>알람 관리</h2>
      <select v-model="statusFilter" class="filter-select">
        <option value="">전체</option>
        <option value="OPEN">OPEN</option>
        <option value="ACKNOWLEDGED">확인됨</option>
        <option value="RESOLVED">해결됨</option>
      </select>
    </div>

    <table class="alarm-table">
      <thead>
        <tr>
          <th>심각도</th>
          <th>유형</th>
          <th>장비 ID</th>
          <th>메시지</th>
          <th>상태</th>
          <th>발생 시각</th>
          <th>조치</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="filteredAlarms.length === 0">
          <td colspan="7" class="empty-row">알람 없음</td>
        </tr>
        <tr v-for="alarm in filteredAlarms" :key="alarm.id" :class="alarm.severity.toLowerCase()">
          <td><span class="sev-badge" :class="alarm.severity.toLowerCase()">{{ alarm.severity }}</span></td>
          <td>{{ alarm.alarm_type }}</td>
          <td>{{ alarm.device_id }}</td>
          <td>{{ alarm.message }}</td>
          <td>{{ alarm.status }}</td>
          <td>{{ formatTime(alarm.created_at) }}</td>
          <td>
            <div class="action-btns">
              <button
                v-if="alarm.status === 'OPEN'"
                class="btn-ack"
                @click="ackAlarm(alarm.id)"
              >확인</button>
              <button class="btn-action" @click="openAction(alarm)">조치</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Action Modal -->
    <div v-if="actionTarget" class="modal-overlay">
      <div class="modal">
        <h3>알람 조치 기록</h3>
        <p class="alarm-msg">{{ actionTarget.message }}</p>
        <div class="field">
          <label>조치 유형</label>
          <select v-model="actionType">
            <option value="REBOOT">장비 재부팅</option>
            <option value="CABLE_CHECK">케이블 점검</option>
            <option value="CONFIG_CHANGE">설정 변경</option>
            <option value="ESCALATE">상위 담당자 에스컬레이션</option>
            <option value="OTHER">기타</option>
          </select>
        </div>
        <div class="field">
          <label>비고</label>
          <textarea v-model="actionNote" rows="3" placeholder="조치 내용을 입력하세요..."></textarea>
        </div>
        <div class="modal-actions">
          <button @click="submitAction">저장</button>
          <button class="cancel" @click="actionTarget = null">취소</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAlarmStore, type Alarm } from "@/stores/alarm";

const alarmStore = useAlarmStore();
const statusFilter = ref("OPEN");
const actionTarget = ref<Alarm | null>(null);
const actionType = ref("OTHER");
const actionNote = ref("");

const filteredAlarms = computed(() => {
  if (!statusFilter.value) return alarmStore.alarms;
  return alarmStore.alarms.filter((a) => a.status === statusFilter.value);
});

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("ko-KR");
}

async function ackAlarm(id: number) {
  await alarmStore.acknowledgeAlarm(id);
}

function openAction(alarm: Alarm) {
  actionTarget.value = alarm;
  actionType.value = "OTHER";
  actionNote.value = "";
}

async function submitAction() {
  if (!actionTarget.value) return;
  await alarmStore.addAction(actionTarget.value.id, actionType.value, actionNote.value);
  actionTarget.value = null;
}

onMounted(() => alarmStore.fetchAlarms());
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
h2 { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); }
.filter-select {
  padding: 0.45rem 0.75rem; border: 1px solid var(--border-input);
  border-radius: 6px; background: var(--bg-input); color: var(--text-primary); outline: none;
}
.alarm-table {
  width: 100%; border-collapse: collapse; background: var(--bg-surface);
  border: 1px solid var(--border-subtle); border-radius: 8px; overflow: hidden;
}
.alarm-table th {
  padding: 0.75rem 1rem; text-align: left; font-size: 0.8rem; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase; background: var(--bg-table-header);
  border-bottom: 1px solid var(--border-subtle);
}
.alarm-table td { padding: 0.85rem 1rem; border-top: 1px solid var(--border-color); font-size: 0.88rem; color: var(--text-primary); }
.sev-badge { padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.78rem; font-weight: 600; }
.sev-badge.critical { background: var(--danger-bg); color: var(--danger); }
.sev-badge.warning { background: rgba(217,130,43,0.2); color: var(--warning); }
.sev-badge.info { background: rgba(29,111,164,0.2); color: var(--accent-hover); }
.action-btns { display: flex; gap: 0.4rem; }
.btn-ack {
  padding: 0.25rem 0.6rem; background: var(--accent-primary); color: white;
  border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
}
.btn-ack:hover { opacity: 0.9; }
.btn-action {
  padding: 0.25rem 0.6rem; background: var(--bg-elevated);
  color: var(--text-secondary); border: 1px solid var(--border-input);
  border-radius: 4px; cursor: pointer; font-size: 0.8rem;
}
.btn-action:hover { background: var(--bg-table-hover); color: var(--text-primary); }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  display: flex; align-items: center; justify-content: center; z-index: 300;
}
.modal {
  background: var(--bg-modal); border: 1px solid var(--border-subtle);
  border-radius: 10px; padding: 1.75rem; width: 420px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}
.modal h3 { margin-bottom: 0.75rem; color: var(--text-primary); }
.alarm-msg {
  color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;
  border-left: 3px solid var(--accent-primary); padding-left: 0.75rem;
}
.field { margin-bottom: 0.75rem; }
.field label { display: block; font-size: 0.82rem; font-weight: 500; color: var(--text-secondary); margin-bottom: 0.3rem; }
.field select, .field textarea {
  width: 100%; padding: 0.5rem 0.7rem; border: 1px solid var(--border-input);
  border-radius: 6px; font-size: 0.9rem; outline: none;
  background: var(--bg-input); color: var(--text-primary);
}
.field textarea { resize: vertical; }
.field select:focus, .field textarea:focus { border-color: var(--accent-primary); }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: flex-end; }
.modal-actions button {
  padding: 0.5rem 1.25rem; border: none; border-radius: 6px;
  cursor: pointer; background: var(--accent-primary); color: white;
}
.modal-actions button:hover { opacity: 0.9; }
.modal-actions button.cancel {
  background: var(--bg-elevated); color: var(--text-secondary);
  border: 1px solid var(--border-input);
}
.modal-actions button.cancel:hover { background: var(--bg-table-hover); color: var(--text-primary); }
.empty-row { text-align: center; color: var(--text-muted); padding: 2rem !important; }
</style>
