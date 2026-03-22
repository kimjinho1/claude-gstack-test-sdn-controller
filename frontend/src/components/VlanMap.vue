<template>
  <div class="vlan-wrap">
    <div v-if="switchPorts.length === 0" class="empty">VLAN 포트 정보 없음</div>
    <div v-else class="boxmap-scroll">
      <table class="boxmap">
        <thead>
          <tr>
            <th class="corner"></th>
            <th v-for="p in switchPorts" :key="p.port_name" class="col-head">
              <div class="port-name-wrap">
                <span class="port-name-txt">{{ shortName(p.port_name) }}</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Mode row -->
          <tr class="row-meta">
            <td class="row-label">Mode</td>
            <td v-for="p in switchPorts" :key="p.port_name" class="cell">
              <span class="badge-mode" :class="p.vlan_mode === 'access' ? 'acc' : 'trk'">
                {{ p.vlan_mode === 'access' ? 'A' : 'T' }}
              </span>
            </td>
          </tr>
          <!-- PVID row -->
          <tr class="row-meta row-pvid">
            <td class="row-label">PVID</td>
            <td v-for="p in switchPorts" :key="p.port_name" class="cell">
              <span class="pvid-val">{{ p.vlan_mode === 'access' ? (p.vlan_id || '—') : (p.pvid || '—') }}</span>
            </td>
          </tr>
          <!-- VLAN ID rows -->
          <tr v-for="vid in allVlanIds" :key="vid" class="row-vlan">
            <td class="row-label">
              <span class="vid-pill">{{ vid }}</span>
              <span v-if="vlanNameMap[vid]" class="vname">{{ vlanNameMap[vid] }}</span>
            </td>
            <td v-for="p in switchPorts" :key="p.port_name" class="cell">
              <span v-if="cellType(p, vid) === 'A'" class="cell-a">A</span>
              <span v-else-if="cellType(p, vid) === 'U'" class="cell-u">U</span>
              <span v-else-if="cellType(p, vid) === 'T'" class="cell-t">T</span>
              <span v-else class="cell-empty">·</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Legend -->
    <div v-if="switchPorts.length > 0" class="legend">
      <span class="leg"><span class="cell-a cell-sm">A</span>Access</span>
      <span class="leg"><span class="cell-u cell-sm">U</span>Native</span>
      <span class="leg"><span class="cell-t cell-sm">T</span>Tagged</span>
      <span class="leg"><span class="badge-mode acc">A</span>Access mode</span>
      <span class="leg"><span class="badge-mode trk">T</span>Trunk mode</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  vlans: any[];
  ports: any[];
}>();

const switchPorts = computed(() => props.ports.filter((p) => p.vlan_mode));

const vlanNameMap = computed(() => {
  const m: Record<string, string> = {};
  for (const v of props.vlans) {
    if (v.vlan_id && v.vlan_name) m[v.vlan_id] = v.vlan_name;
  }
  return m;
});

const allVlanIds = computed(() => {
  const ids = new Set<string>();
  for (const p of switchPorts.value) {
    if (p.vlan_mode === "access" && p.vlan_id) {
      ids.add(String(p.vlan_id));
    } else if (p.vlan_mode === "trunk") {
      if (p.pvid) ids.add(String(p.pvid));
      if (p.tagged_vlans) {
        p.tagged_vlans.split(",").forEach((v: string) => {
          const t = v.trim();
          if (t) ids.add(t);
        });
      }
    }
  }
  return [...ids].sort((a, b) => parseInt(a) - parseInt(b));
});

function cellType(port: any, vid: string): "A" | "U" | "T" | null {
  if (port.vlan_mode === "access") {
    return String(port.vlan_id) === vid ? "A" : null;
  }
  if (port.vlan_mode === "trunk") {
    if (String(port.pvid) === vid) return "U";
    if (port.tagged_vlans) {
      const tagged = port.tagged_vlans.split(",").map((v: string) => v.trim());
      if (tagged.includes(vid)) return "T";
    }
  }
  return null;
}

// Extract only the numeric/slash part after the interface type name
function shortName(name: string): string {
  const m = name.match(/(\d[\d/.]*)$/);
  return m ? m[1] : name;
}
</script>

<style scoped>
.vlan-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}

/* Scrollable map area */
.boxmap-scroll {
  overflow-x: auto;
  overflow-y: visible;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
}

/* Table */
.boxmap {
  border-collapse: collapse;
  table-layout: fixed;
}

/* Corner (top-left blank) */
.corner {
  width: 80px;
  min-width: 80px;
  border-bottom: 2px solid var(--border-subtle);
}

/* Port column headers — horizontal, two-line abbreviation */
.col-head {
  width: 46px;
  min-width: 46px;
  padding: 5px 2px;
  vertical-align: bottom;
  text-align: center;
  border-bottom: 2px solid var(--border-subtle);
  border-left: 1px solid var(--border-color);
}
.port-name-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}
.port-name-txt {
  font-size: 0.72rem;
  font-family: monospace;
  color: var(--text-muted);
  text-align: center;
  white-space: nowrap;
}

/* Row label column */
.row-label {
  padding: 0 8px 0 10px;
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
  font-weight: 500;
  text-align: right;
  border-right: 2px solid var(--border-subtle);
  vertical-align: middle;
  height: 28px;
}

/* VLAN label with pill + name */
.vid-pill {
  font-size: 0.78rem;
  font-weight: 700;
  color: #818cf8;
  font-family: monospace;
}
.vname {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-left: 4px;
}

/* Data cells */
.cell {
  text-align: center;
  vertical-align: middle;
  padding: 2px;
  height: 28px;
  width: 38px;
  border: 1px solid var(--border-color);
}

/* Meta rows (Mode, PVID) */
.row-meta .cell {
  background: rgba(255,255,255,0.025);
}
.row-pvid .cell {
  border-bottom: 2px solid var(--border-subtle);
}

/* Mode badge (small, in cell) */
.badge-mode {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 800;
  font-family: monospace;
}
.acc { background: rgba(34,197,94,0.18); color: #22c55e; }
.trk { background: rgba(251,146,60,0.18); color: #fb923c; }

/* PVID value */
.pvid-val {
  font-size: 0.72rem;
  font-family: monospace;
  color: var(--text-secondary);
}

.cell-empty {
  color: var(--border-subtle);
  font-size: 0.78rem;
  opacity: 0.4;
}

/* A / U / T cells */
.cell-a, .cell-u, .cell-t {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  font-size: 0.78rem;
  font-weight: 800;
}
.cell-a { background: rgba(59,130,246,0.28); color: #60a5fa; }
.cell-u { background: rgba(34,197,94,0.22); color: #4ade80; }
.cell-t { background: rgba(251,146,60,0.22); color: #fb923c; }

.cell-sm {
  width: 17px;
  height: 17px;
  font-size: 0.68rem;
}

/* Legend */
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.15rem 0;
}
.leg {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  color: var(--text-muted);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
  font-size: 0.85rem;
}
</style>
