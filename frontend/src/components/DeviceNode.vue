<template>
  <div class="device-node" :class="statusClass">
    <Handle type="target" :position="Position.Top" />
    <div class="node-header">
      <span class="status-dot" />
      <span class="node-name">{{ data.name }}</span>
    </div>
    <div class="node-ip">{{ data.ip_addr }}</div>
    <div class="node-footer">
      <span class="badge proto">{{ data.protocol }}</span>
      <span class="badge" :class="statusClass">{{ data.status }}</span>
    </div>
    <Handle type="source" :position="Position.Bottom" />

    <!-- Hover tooltip -->
    <div class="node-tooltip">
      <div v-if="data.model || data.catalog_model" class="tt-row">
        <span class="tt-label">모델</span>
        <span class="tt-value">{{ data.model || data.catalog_model }}</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">MAC</span>
        <span class="tt-value mono">{{ data.mac_addr }}</span>
      </div>
      <div v-if="data.serial_no" class="tt-row">
        <span class="tt-label">S/N</span>
        <span class="tt-value mono">{{ data.serial_no }}</span>
      </div>
      <div v-if="data.sw_version" class="tt-row">
        <span class="tt-label">SW</span>
        <span class="tt-value mono">{{ data.sw_version }}</span>
      </div>
      <div v-if="data.uptime" class="tt-row">
        <span class="tt-label">Uptime</span>
        <span class="tt-value">{{ data.uptime }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: {
    id: number
    name: string
    ip_addr: string
    mac_addr: string
    status: string
    protocol: string
    model: string | null
    model_id: number | null
    catalog_model: string | null
    serial_no: string | null
    sw_version: string | null
    uptime: string | null
  }
}>()

const statusClass = computed(() => props.data.status.toLowerCase())
</script>

<style scoped>
.device-node {
  background: var(--bg-surface);
  border: 1.5px solid var(--border-input);
  border-radius: 6px;
  padding: 10px 14px;
  min-width: 180px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: 'Inter', 'Segoe UI', sans-serif;
  position: relative;
}
.device-node:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent-primary) 25%, transparent);
}

/* Tooltip */
.node-tooltip {
  display: none;
  position: absolute;
  left: calc(100% + 10px);
  top: 0;
  background: var(--bg-modal);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 8px 12px;
  min-width: 220px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  z-index: 9999;
  pointer-events: none;
  white-space: nowrap;
}
.device-node:hover .node-tooltip {
  display: block;
}
.tt-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 2px 0;
}
.tt-label {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 48px;
  flex-shrink: 0;
}
.tt-value {
  font-size: 0.78rem;
  color: var(--text-primary);
}
.tt-value.mono {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.74rem;
}
.device-node.managed  { border-left: 3px solid var(--success); }
.device-node.error    { border-left: 3px solid var(--danger); }
.device-node.pending  { border-left: 3px solid var(--warning); }
.device-node.unregistered { border-left: 3px solid var(--text-muted); }

.node-header {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 3px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--text-muted);
}
.managed  .status-dot { background: var(--success); box-shadow: 0 0 6px color-mix(in srgb, var(--success) 60%, transparent); }
.error    .status-dot { background: var(--danger);  box-shadow: 0 0 6px color-mix(in srgb, var(--danger) 60%, transparent); }
.pending  .status-dot { background: var(--warning); box-shadow: 0 0 6px color-mix(in srgb, var(--warning) 50%, transparent); }

.node-name {
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}
.node-ip {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-bottom: 7px;
  padding-left: 15px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.node-footer { display: flex; gap: 5px; }
.badge {
  font-size: 0.62rem;
  padding: 1px 6px;
  border-radius: 2px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.badge.proto       { background: var(--accent-active-bg); color: var(--accent-hover); }
.badge.managed     { background: rgba(0,168,84,0.15); color: var(--success); }
.badge.error       { background: var(--danger-bg); color: var(--danger); }
.badge.pending     { background: rgba(217,130,43,0.15); color: var(--warning); }
.badge.unregistered { background: var(--bg-elevated); color: var(--text-muted); }
</style>
