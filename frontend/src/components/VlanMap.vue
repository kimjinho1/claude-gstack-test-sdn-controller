<template>
  <div class="vlan-wrap">
    <!-- VLAN list -->
    <div class="section-title">VLAN 목록</div>
    <table class="data-table">
      <thead>
        <tr><th>VLAN ID</th><th>이름</th></tr>
      </thead>
      <tbody>
        <tr v-if="vlans.length === 0">
          <td colspan="2" class="empty">VLAN 정보 없음</td>
        </tr>
        <tr v-for="v in vlans" :key="v.id">
          <td class="mono vlan-id-cell">
            <span class="vlan-badge">{{ v.vlan_id }}</span>
          </td>
          <td>{{ v.vlan_name || "—" }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Per-port VLAN assignment -->
    <div class="section-title" style="margin-top: 1.5rem;">포트별 VLAN 할당</div>
    <table class="data-table">
      <thead>
        <tr>
          <th>포트</th>
          <th>모드</th>
          <th>Access VLAN / Native</th>
          <th>Tagged VLANs</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="portsWithVlan.length === 0">
          <td colspan="4" class="empty">VLAN 할당 정보 없음</td>
        </tr>
        <tr v-for="p in portsWithVlan" :key="p.id">
          <td class="mono">{{ p.port_name }}</td>
          <td>
            <span class="mode-badge" :class="p.vlan_mode === 'access' ? 'mode-access' : 'mode-trunk'">
              {{ p.vlan_mode?.toUpperCase() }}
            </span>
          </td>
          <td class="mono">
            <span v-if="p.vlan_mode === 'access'">
              <span class="vlan-badge">{{ p.vlan_id || "—" }}</span>
              <span class="vlan-name">{{ vlanName(p.vlan_id) }}</span>
            </span>
            <span v-else-if="p.vlan_mode === 'trunk'">
              <span class="vlan-badge">{{ p.pvid || "—" }}</span>
              <span class="vlan-name">{{ vlanName(p.pvid) }}</span>
            </span>
          </td>
          <td>
            <span v-if="p.tagged_vlans" class="tagged-vlans">
              <span
                v-for="vid in p.tagged_vlans.split(',')"
                :key="vid"
                class="vlan-badge vlan-badge-sm"
              >{{ vid.trim() }}</span>
            </span>
            <span v-else class="txt-muted">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  vlans: any[];
  ports: any[];
}>();

// Build vlan_id → name lookup
const vlanNameMap = computed(() => {
  const m: Record<string, string> = {};
  for (const v of props.vlans) {
    if (v.vlan_id && v.vlan_name) m[v.vlan_id] = v.vlan_name;
  }
  return m;
});

function vlanName(vid: string | null | undefined): string {
  if (!vid) return "";
  const name = vlanNameMap.value[vid];
  return name ? ` (${name})` : "";
}

// Only show ports that have VLAN info
const portsWithVlan = computed(() =>
  props.ports.filter((p) => p.vlan_mode)
);
</script>

<style scoped>
.vlan-wrap { display: flex; flex-direction: column; gap: 0; }
.section-title { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  padding: 0.55rem 0.75rem;
  text-align: left;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-subtle);
}
.data-table td {
  padding: 0.65rem 0.75rem;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}
.mono { font-family: monospace; }
.empty { text-align: center; color: var(--text-muted); padding: 2rem !important; }
.txt-muted { color: var(--text-muted); }

.vlan-id-cell { vertical-align: middle; }
.vlan-badge {
  display: inline-block;
  background: rgba(99,102,241,0.15);
  color: #818cf8;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  font-family: monospace;
}
.vlan-badge-sm { font-size: 0.72rem; padding: 1px 5px; margin: 1px; }
.vlan-name { color: var(--text-muted); font-size: 0.8rem; margin-left: 0.25rem; font-family: sans-serif; }

.mode-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.mode-access { background: rgba(34,197,94,0.12); color: #22c55e; }
.mode-trunk { background: rgba(251,146,60,0.12); color: #fb923c; }

.tagged-vlans { display: flex; flex-wrap: wrap; gap: 2px; }
</style>
