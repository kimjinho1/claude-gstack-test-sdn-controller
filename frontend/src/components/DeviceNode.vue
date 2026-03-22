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
    status: string
    protocol: string
    model: string | null
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
}
.device-node:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(29, 111, 164, 0.25);
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
.managed  .status-dot { background: var(--success); box-shadow: 0 0 6px rgba(0,168,84,0.6); }
.error    .status-dot { background: var(--danger); box-shadow: 0 0 6px rgba(194,48,48,0.6); }
.pending  .status-dot { background: var(--warning); box-shadow: 0 0 6px rgba(217,130,43,0.5); }

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
