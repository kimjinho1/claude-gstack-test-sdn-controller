<template>
  <div class="switch-wrap">
    <!-- Switch chassis -->
    <div class="switch-chassis">
      <div class="chassis-label">{{ label }}</div>
      <div class="ports-grid" @mouseleave="hovered = null">
        <div
          v-for="(port, idx) in ports"
          :key="port.id"
          class="port-box"
          :class="portClass(port)"
          @mouseenter="onPortEnter(port, $event)"
        >
          <div class="port-led"></div>
          <div class="port-name">{{ shortName(port.port_name) }}</div>
        </div>
      </div>

      <!-- Tooltip rendered in <body> via Teleport — escapes all overflow/stacking contexts -->
      <Teleport to="body">
        <div v-if="hovered" class="port-tooltip-global" :style="tooltipStyle">
          <div class="tooltip-header">
            <span class="tooltip-portname">{{ hovered.port_name }}</span>
            <span class="tooltip-badge" :class="hovered.port_status === 'UP' ? 'badge-up' : 'badge-down'">
              {{ hovered.port_status }}
            </span>
          </div>
          <div class="tooltip-row" v-if="hovered.description">
            <span class="tl">설명</span><span class="tv">{{ hovered.description }}</span>
          </div>
          <div class="tooltip-row">
            <span class="tl">Admin</span>
            <span class="tv" :class="hovered.admin_status === 'down' ? 'txt-red' : 'txt-green'">
              {{ hovered.admin_status === 'down' ? 'shutdown' : 'no shutdown' }}
            </span>
          </div>
          <div class="tooltip-row" v-if="hovered.port_type">
            <span class="tl">타입</span><span class="tv">{{ hovered.port_type }}</span>
          </div>
          <div class="tooltip-row" v-if="hovered.speed || hovered.duplex">
            <span class="tl">속도</span>
            <span class="tv">{{ [hovered.speed, hovered.duplex].filter(Boolean).join(' / ') }}</span>
          </div>
          <div class="tooltip-row" v-if="hovered.vlan_mode">
            <span class="tl">VLAN</span>
            <span class="tv">
              {{ hovered.vlan_mode === 'access' ? `Access ${hovered.vlan_id || ''}` : `Trunk (native: ${hovered.pvid || '—'})` }}
            </span>
          </div>
          <div class="tooltip-divider" v-if="hovered.traffic_in_bps !== null || hovered.traffic_out_bps !== null"></div>
          <div class="tooltip-row" v-if="hovered.traffic_in_bps !== null">
            <span class="tl">수신</span><span class="tv txt-green">↓ {{ formatBps(hovered.traffic_in_bps) }}</span>
          </div>
          <div class="tooltip-row" v-if="hovered.traffic_out_bps !== null">
            <span class="tl">송신</span><span class="tv txt-blue">↑ {{ formatBps(hovered.traffic_out_bps) }}</span>
          </div>
        </div>
      </Teleport>
    </div>

    <!-- Legend -->
    <div class="legend">
      <span class="legend-item"><span class="led-sample led-up"></span>UP</span>
      <span class="legend-item"><span class="led-sample led-down"></span>DOWN</span>
      <span class="legend-item"><span class="led-sample led-shutdown"></span>Shutdown</span>
    </div>

    <!-- Port list table (hidden in compact mode) -->
    <table v-if="!compact" class="port-table">
      <thead>
        <tr>
          <th>포트</th>
          <th>상태</th>
          <th>Admin</th>
          <th>타입</th>
          <th>속도</th>
          <th>VLAN</th>
          <th>수신 bps</th>
          <th>송신 bps</th>
          <th>설명</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="ports.length === 0">
          <td colspan="9" class="empty">포트 정보 없음</td>
        </tr>
        <tr v-for="p in ports" :key="p.port_name" :class="{ 'row-down': p.port_status === 'DOWN' && p.admin_status !== 'down' }">
          <td class="mono">{{ p.port_name }}</td>
          <td>
            <span class="badge" :class="p.port_status === 'UP' ? 'badge-up' : 'badge-down'">
              {{ p.port_status }}
            </span>
          </td>
          <td>
            <span v-if="p.admin_status === 'down'" class="badge badge-shutdown">shutdown</span>
            <span v-else class="txt-muted">—</span>
          </td>
          <td class="txt-muted small">{{ p.port_type || "—" }}</td>
          <td class="small">{{ p.speed || "—" }}</td>
          <td class="small">
            <span v-if="p.vlan_mode === 'access'">A:{{ p.vlan_id || "—" }}</span>
            <span v-else-if="p.vlan_mode === 'trunk'">T({{ p.pvid || "—" }})</span>
            <span v-else class="txt-muted">—</span>
          </td>
          <td class="small mono">{{ formatBps(p.traffic_in_bps) }}</td>
          <td class="small mono">{{ formatBps(p.traffic_out_bps) }}</td>
          <td class="small txt-muted">{{ p.description || "—" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  ports: any[];
  label?: string;
  compact?: boolean;
}>();

const hovered = ref<any>(null);
const tooltipStyle = ref<Record<string, string>>({});

const TOOLTIP_W = 220;
const GAP = 8;

function onPortEnter(port: any, e: MouseEvent) {
  hovered.value = port;
  const el = e.currentTarget as HTMLElement;
  const rect = el.getBoundingClientRect();

  // Center on port, clamped to viewport edges
  let left = rect.left + rect.width / 2 - TOOLTIP_W / 2;
  left = Math.max(GAP, Math.min(window.innerWidth - TOOLTIP_W - GAP, left));

  // position: fixed via Teleport escapes all parent overflow/clip/stacking contexts
  tooltipStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    bottom: `${window.innerHeight - rect.top + GAP}px`,
    top: 'auto',
    transform: 'none',
  };
}

function portClass(port: any) {
  if (port.admin_status === "down") return "port-shutdown";
  if (port.port_status === "UP") return "port-up";
  return "port-down";
}

const SHORT_MAP: [RegExp, string][] = [
  [/^GigabitEthernet/, "Gi"],
  [/^TenGigabitEthernet/, "Te"],
  [/^FastEthernet/, "Fa"],
  [/^HundredGigabitEthernet/, "Hu"],
  [/^FortyGigabitEthernet/, "Fo"],
  [/^Ethernet/, "Et"],
  [/^Management/, "Ma"],
  [/^Loopback/, "Lo"],
  [/^Vlan/, "Vl"],
];

function shortName(name: string): string {
  for (const [re, abbr] of SHORT_MAP) {
    if (re.test(name)) return name.replace(re, abbr);
  }
  return name.length > 6 ? name.slice(0, 6) : name;
}

function formatBps(bps: number | null | undefined): string {
  if (bps === null || bps === undefined) return "—";
  if (bps < 1000) return `${Math.round(bps)} bps`;
  if (bps < 1_000_000) return `${(bps / 1000).toFixed(1)} Kbps`;
  return `${(bps / 1_000_000).toFixed(1)} Mbps`;
}
</script>

<style scoped>
.switch-wrap { display: flex; flex-direction: column; gap: 1rem; }

/* Switch chassis */
.switch-chassis {
  background: #1a1a2e;
  border: 1px solid #2d2d4e;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.chassis-label { font-size: 0.82rem; color: #6b7280; font-family: monospace; }
.ports-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* Port box */
.port-box {
  width: 52px;
  height: 52px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  cursor: pointer;
  position: relative;
  transition: transform 0.1s, box-shadow 0.1s;
  border: 1px solid rgba(255,255,255,0.06);
}
.port-box:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.4); z-index: 10; }

.port-up { background: #14532d; }
.port-down { background: #450a0a; }
.port-shutdown { background: #1f2937; }

.port-led {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.port-up .port-led { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.port-down .port-led { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
.port-shutdown .port-led { background: #4b5563; }

.port-name { font-size: 0.7rem; color: #d1d5db; font-family: monospace; line-height: 1; }

/* Tooltip — position: fixed is set via JS to escape parent overflow clipping */
.port-tooltip {
  position: fixed;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 0.6rem 0.75rem;
  min-width: 200px;
  z-index: 9999;
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  white-space: nowrap;
  pointer-events: none;
}
.port-tooltip::after {
  content: none; /* arrow removed — fixed positioning makes alignment unreliable */
}
.tooltip-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.tooltip-portname { font-size: 0.85rem; font-weight: 600; color: #f3f4f6; font-family: monospace; }
.tooltip-badge { font-size: 0.7rem; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.badge-up { background: rgba(34,197,94,0.2); color: #22c55e; }
.badge-down { background: rgba(239,68,68,0.2); color: #ef4444; }
.tooltip-row { display: flex; gap: 0.5rem; align-items: baseline; font-size: 0.78rem; line-height: 1.6; }
.tl { color: #6b7280; min-width: 40px; flex-shrink: 0; }
.tv { color: #d1d5db; }
.txt-green { color: #22c55e; }
.txt-red { color: #ef4444; }
.txt-blue { color: #60a5fa; }
.tooltip-divider { border-top: 1px solid #374151; margin: 0.4rem 0; }

/* Legend */
.legend { display: flex; gap: 1rem; align-items: center; }
.legend-item { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--text-muted); }
.led-sample { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.led-up { background: #22c55e; box-shadow: 0 0 4px #22c55e; }
.led-down { background: #ef4444; box-shadow: 0 0 4px #ef4444; }
.led-shutdown { background: #4b5563; }

/* Port table */
.port-table { width: 100%; border-collapse: collapse; }
.port-table th {
  padding: 0.55rem 0.75rem;
  text-align: left;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-subtle);
}
.port-table td {
  padding: 0.6rem 0.75rem;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}
.row-down td { background: rgba(239,68,68,0.04); }
.mono { font-family: monospace; }
.small { font-size: 0.82rem; }
.txt-muted { color: var(--text-muted); }
.empty { text-align: center; color: var(--text-muted); padding: 2rem !important; }

.badge { font-size: 0.72rem; font-weight: 600; padding: 2px 7px; border-radius: 4px; }
.badge-shutdown { background: rgba(107,114,128,0.15); color: #9ca3af; }
</style>

<!-- Global style for Teleport tooltip — not scoped because it renders in <body> -->
<style>
.port-tooltip-global {
  position: fixed;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 0.6rem 0.75rem;
  min-width: 200px;
  z-index: 9999;
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  white-space: nowrap;
  pointer-events: none;
}
.port-tooltip-global .tooltip-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.port-tooltip-global .tooltip-portname { font-size: 0.85rem; font-weight: 600; color: #f3f4f6; font-family: monospace; }
.port-tooltip-global .tooltip-badge { font-size: 0.7rem; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.port-tooltip-global .badge-up { background: rgba(34,197,94,0.2); color: #22c55e; }
.port-tooltip-global .badge-down { background: rgba(239,68,68,0.2); color: #ef4444; }
.port-tooltip-global .tooltip-row { display: flex; gap: 0.5rem; align-items: baseline; font-size: 0.78rem; line-height: 1.6; }
.port-tooltip-global .tl { color: #6b7280; min-width: 40px; flex-shrink: 0; }
.port-tooltip-global .tv { color: #d1d5db; }
.port-tooltip-global .txt-green { color: #22c55e; }
.port-tooltip-global .txt-red { color: #ef4444; }
.port-tooltip-global .txt-blue { color: #60a5fa; }
.port-tooltip-global .tooltip-divider { border-top: 1px solid #374151; margin: 0.4rem 0; }
</style>
