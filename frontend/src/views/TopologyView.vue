<template>
  <div class="topo-wrap">
    <!-- Toolbar -->
    <div class="topo-toolbar">
      <div class="toolbar-left">
        <span class="topo-title">네트워크 토폴로지</span>
        <div class="topo-stats">
          <span class="stat managed">● MANAGED {{ managedCount }}</span>
          <span class="stat error">● ERROR {{ errorCount }}</span>
          <span class="stat pending">● PENDING {{ pendingCount }}</span>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn-tool" @click="doLayout" title="레이아웃 재정렬">⟳ 정렬</button>
        <button class="btn-tool" @click="doFitView" title="화면에 맞추기">⊞ 맞춤</button>
        <button class="btn-tool-primary" @click="showAddLink = true">+ 링크 추가</button>
      </div>
    </div>

    <!-- Canvas -->
    <div class="topo-canvas">
      <div v-if="loading" class="topo-loading">
        <span class="loading-spinner" />
        <span>토폴로지 로딩 중...</span>
      </div>

      <VueFlow
        v-else
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :default-edge-options="defaultEdgeOptions"
        :connect-on-click="false"
        :delete-key-code="null"
        fit-view-on-init
        @connect="onConnect"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
        @pane-click="selectedEdgeId = null"
      >
        <Background
          :variant="BackgroundVariant.Dots"
          :gap="28"
          :size="1.2"
        />
        <Controls :show-interactive="false" class="topo-controls" />
        <MiniMap
          :node-color="minimapColor"
          node-border-radius="3"
          mask-color="rgba(8,13,20,0.85)"
          class="topo-minimap"
        />
      </VueFlow>
    </div>

    <!-- Edge selected → delete bar -->
    <Transition name="slide-up">
      <div v-if="selectedEdgeId" class="edge-action-bar">
        <span>
          링크 선택됨:
          <strong>{{ selectedEdgeLabel }}</strong>
        </span>
        <button class="btn-danger-sm" @click="deleteEdge">링크 삭제</button>
        <button class="btn-cancel-sm" @click="selectedEdgeId = null">닫기</button>
      </div>
    </Transition>

    <!-- Error banner -->
    <div v-if="topologyError" class="topo-error-banner">{{ topologyError }}</div>

    <!-- Add link modal -->
    <Transition name="fade">
      <div v-if="showAddLink" class="modal-overlay" @click.self="closeAddLink">
        <div class="modal-dark">
          <div class="modal-hd">
            <h3>링크 추가</h3>
            <button class="modal-close" @click="closeAddLink">✕</button>
          </div>
          <div class="modal-bd">
            <div class="form-field">
              <label>상위 장비 (부모)</label>
              <select v-model="linkForm.parent_id">
                <option value="" disabled>장비 선택...</option>
                <option v-for="d in allDevices" :key="d.id" :value="d.id">
                  {{ d.name }} — {{ d.ip_addr }}
                </option>
              </select>
            </div>
            <div class="link-arrow">↓</div>
            <div class="form-field">
              <label>하위 장비 (자식)</label>
              <select v-model="linkForm.child_id">
                <option value="" disabled>장비 선택...</option>
                <option
                  v-for="d in allDevices"
                  :key="d.id"
                  :value="d.id"
                  :disabled="d.id === linkForm.parent_id"
                >
                  {{ d.name }} — {{ d.ip_addr }}
                </option>
              </select>
            </div>
            <p v-if="linkError" class="form-error">{{ linkError }}</p>
          </div>
          <div class="modal-ft">
            <button class="btn-cancel" @click="closeAddLink">취소</button>
            <button
              class="btn-primary-dark"
              :disabled="!linkForm.parent_id || !linkForm.child_id || linkLoading"
              @click="submitAddLink"
            >
              {{ linkLoading ? '추가 중...' : '링크 추가' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import {
  VueFlow,
  useVueFlow,
  MarkerType,
  type Node,
  type Edge,
  type NodeMouseEvent,
  type EdgeMouseEvent,
  type Connection,
} from '@vue-flow/core'
import { Background, BackgroundVariant } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import dagre from 'dagre'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import DeviceNode from '@/components/DeviceNode.vue'
import api from '@/api/client'

// ── types ──────────────────────────────────────────────────────────────────
interface DeviceData {
  id: number
  name: string
  ip_addr: string
  status: string
  protocol: string
  model: string | null
}
interface LinkData {
  id: number
  parent_id: number
  child_id: number
}

// ── state ──────────────────────────────────────────────────────────────────
const router = useRouter()
const { fitView } = useVueFlow()

const loading = ref(true)
const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const allDevices = ref<DeviceData[]>([])
const linkMap = ref<Map<string, number>>(new Map()) // "srcId-tgtId" → link.id
const topologyError = ref('')

const showAddLink = ref(false)
const linkForm = ref<{ parent_id: number | ''; child_id: number | '' }>({
  parent_id: '',
  child_id: '',
})
const linkError = ref('')
const linkLoading = ref(false)

const selectedEdgeId = ref<string | null>(null)

const nodeTypes = { device: markRaw(DeviceNode) }

const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: false,
  markerEnd: { type: MarkerType.ArrowClosed, color: '#1d6fa4', width: 18, height: 18 },
  style: { stroke: '#1d6fa4', strokeWidth: 1.8 },
}

// ── computed ───────────────────────────────────────────────────────────────
const managedCount = computed(() =>
  allDevices.value.filter(d => d.status === 'MANAGED').length
)
const errorCount = computed(() =>
  allDevices.value.filter(d => d.status === 'ERROR').length
)
const pendingCount = computed(() =>
  allDevices.value.filter(d => d.status === 'PENDING').length
)

const selectedEdgeLabel = computed(() => {
  if (!selectedEdgeId.value) return ''
  const edge = edges.value.find(e => e.id === selectedEdgeId.value)
  if (!edge) return ''
  const parent = allDevices.value.find(d => String(d.id) === edge.source)
  const child = allDevices.value.find(d => String(d.id) === edge.target)
  return `${parent?.name ?? edge.source} → ${child?.name ?? edge.target}`
})

// ── dagre layout ───────────────────────────────────────────────────────────
function applyLayout(ns: Node[], es: Edge[]): Node[] {
  if (ns.length === 0) return ns // dagre produces NaN positions for empty graphs
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', ranksep: 90, nodesep: 55, marginx: 40, marginy: 40 })

  ns.forEach(n => g.setNode(n.id, { width: 200, height: 80 }))
  es.forEach(e => g.setEdge(e.source, e.target))
  dagre.layout(g)

  return ns.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - 100, y: pos.y - 40 } }
  })
}

// ── data loading ───────────────────────────────────────────────────────────
async function loadTopology() {
  loading.value = true
  try {
    const { data } = await api.get('/device-links/graph')
    allDevices.value = data.devices

    const newNodes: Node[] = data.devices.map((d: DeviceData) => ({
      id: String(d.id),
      type: 'device',
      position: { x: 0, y: 0 },
      data: d,
    }))

    const newEdges: Edge[] = data.links.map((l: LinkData) => ({
      id: `e-${l.id}`,
      source: String(l.parent_id),
      target: String(l.child_id),
      ...defaultEdgeOptions,
    }))

    // Build lookup map
    linkMap.value = new Map(
      data.links.map((l: LinkData) => [`${l.parent_id}-${l.child_id}`, l.id])
    )

    nodes.value = applyLayout(newNodes, newEdges)
    edges.value = newEdges
  } finally {
    loading.value = false
  }
}

// ── actions ────────────────────────────────────────────────────────────────
function doLayout() {
  nodes.value = applyLayout([...nodes.value], edges.value)
}

function doFitView() {
  fitView({ padding: 0.12 })
}

function minimapColor(node: Node): string {
  const status = node.data?.status
  if (status === 'MANAGED') return '#0f9960'
  if (status === 'ERROR') return '#db3737'
  if (status === 'PENDING') return '#d9822b'
  return '#5c7080'
}

// drag-to-connect creates a new link
async function onConnect(params: Connection) {
  if (!params.source || !params.target) return
  await createLink(Number(params.source), Number(params.target))
}

function onNodeClick({ node }: NodeMouseEvent) {
  router.push(`/devices/${node.data.id}`)
}

function onEdgeClick({ edge }: EdgeMouseEvent) {
  selectedEdgeId.value = selectedEdgeId.value === edge.id ? null : edge.id
}

async function deleteEdge() {
  if (!selectedEdgeId.value) return
  const edge = edges.value.find(e => e.id === selectedEdgeId.value)
  if (!edge) return
  const linkId = linkMap.value.get(`${edge.source}-${edge.target}`)
  if (!linkId) return
  try {
    await api.delete(`/device-links/${linkId}`)
  } catch {
    topologyError.value = '링크 삭제에 실패했습니다. 다시 시도하세요.'
    return // keep edge in place on failure
  }
  edges.value = edges.value.filter(e => e.id !== selectedEdgeId.value)
  linkMap.value.delete(`${edge.source}-${edge.target}`)
  selectedEdgeId.value = null
  topologyError.value = ''
}

// shared create link logic
async function createLink(parentId: number, childId: number) {
  const key = `${parentId}-${childId}`
  if (linkMap.value.has(key)) return // already exists
  try {
    const { data } = await api.post('/device-links', { parent_id: parentId, child_id: childId })
    const newEdge: Edge = {
      id: `e-${data.id}`,
      source: String(parentId),
      target: String(childId),
      ...defaultEdgeOptions,
    }
    edges.value = [...edges.value, newEdge]
    linkMap.value.set(key, data.id)
  } catch (e: any) {
    if (e.response?.status !== 409) {
      // Only swallow 409 (duplicate) — anything else is a real error
      throw e
    }
  }
}

// modal add link
async function submitAddLink() {
  if (!linkForm.value.parent_id || !linkForm.value.child_id) return
  if (linkForm.value.parent_id === linkForm.value.child_id) {
    linkError.value = '상위/하위 장비가 같을 수 없습니다.'
    return
  }
  linkError.value = ''
  linkLoading.value = true
  try {
    await createLink(Number(linkForm.value.parent_id), Number(linkForm.value.child_id))
    closeAddLink()
  } catch (e: any) {
    linkError.value = e.response?.data?.detail || '링크 생성 실패'
  } finally {
    linkLoading.value = false
  }
}

function closeAddLink() {
  showAddLink.value = false
  linkForm.value = { parent_id: '', child_id: '' }
  linkError.value = ''
}

// ── lifecycle ──────────────────────────────────────────────────────────────
onMounted(loadTopology)
</script>

<style scoped>
/* ── container ─────────────────────────────────────────────────────────── */
.topo-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  position: relative;
}

/* ── toolbar ─────────────────────────────────────────────────────────────── */
.topo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 1.1rem;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 1rem;
  flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; }
.toolbar-right { display: flex; align-items: center; gap: 0.5rem; }

.topo-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.topo-stats { display: flex; gap: 1rem; }
.stat { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em; }
.stat.managed { color: var(--success); }
.stat.error   { color: var(--danger); }
.stat.pending { color: var(--warning); }

.btn-tool {
  padding: 0.32rem 0.75rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border-input);
  color: var(--text-secondary);
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}
.btn-tool:hover { background: var(--bg-table-hover); color: var(--text-primary); border-color: var(--text-muted); }

.btn-tool-primary {
  padding: 0.32rem 0.85rem;
  background: var(--accent-primary);
  border: none;
  color: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  transition: opacity 0.15s;
}
.btn-tool-primary:hover { opacity: 0.9; }

/* ── canvas ──────────────────────────────────────────────────────────────── */
.topo-canvas {
  flex: 1;
  min-height: 0;
  position: relative;
}
.flow-instance { width: 100%; height: 100%; }

/* Loading */
.topo-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  background: var(--bg-base);
  color: var(--text-muted);
  font-size: 0.9rem;
}
.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* VueFlow overrides */
:deep(.vue-flow__background) { background: var(--bg-base) !important; }
:deep(.vue-flow__edge-path) { stroke: var(--accent-primary) !important; }
:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: var(--accent-hover) !important;
  stroke-width: 2.5px !important;
}
:deep(.vue-flow__handle) {
  background: var(--accent-primary) !important;
  border-color: var(--bg-base) !important;
  width: 10px !important;
  height: 10px !important;
}
:deep(.vue-flow__handle:hover) { background: var(--accent-hover) !important; }
:deep(.vue-flow__node.selected > *) {
  box-shadow: 0 0 0 2px var(--accent-primary), 0 0 16px rgba(29,111,164,0.4) !important;
}

/* Controls theme */
:deep(.topo-controls) {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 4px !important;
  overflow: hidden;
}
:deep(.topo-controls button) {
  background: var(--bg-surface) !important;
  color: var(--text-secondary) !important;
  border-color: var(--border-subtle) !important;
}
:deep(.topo-controls button:hover) { background: var(--bg-elevated) !important; color: var(--text-primary) !important; }
:deep(.topo-controls path) { fill: var(--text-secondary) !important; }

/* Minimap */
:deep(.topo-minimap) {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: 4px !important;
}

/* ── edge action bar ─────────────────────────────────────────────────────── */
.edge-action-bar {
  position: absolute;
  bottom: 1.2rem;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-surface);
  border: 1px solid var(--border-input);
  border-radius: 6px;
  padding: 0.55rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.82rem;
  color: var(--text-secondary);
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  z-index: 50;
  white-space: nowrap;
}
.edge-action-bar strong { color: var(--text-primary); }
.topo-error-banner {
  position: absolute; bottom: 1rem; left: 50%; transform: translateX(-50%);
  background: var(--danger-bg); color: #ff6b6b; border: 1px solid var(--danger);
  padding: 0.5rem 1rem; border-radius: 4px; font-size: 0.82rem; z-index: 500;
}

.btn-danger-sm {
  padding: 0.28rem 0.75rem;
  background: var(--danger-bg);
  border: 1px solid var(--danger);
  color: var(--danger);
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 600;
  transition: all 0.15s;
}
.btn-danger-sm:hover { opacity: 0.8; }
.btn-cancel-sm {
  padding: 0.28rem 0.65rem;
  background: transparent;
  border: 1px solid var(--border-input);
  color: var(--text-muted);
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.78rem;
}
.btn-cancel-sm:hover { color: var(--text-primary); }

/* ── modal ───────────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
}
.modal-dark {
  background: var(--bg-modal);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  width: 380px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.modal-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
}
.modal-hd h3 { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 2px 6px;
}
.modal-close:hover { color: var(--text-primary); }

.modal-bd { padding: 1.25rem; }
.form-field { margin-bottom: 0.8rem; }
.form-field label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
}
.form-field select {
  width: 100%;
  padding: 0.5rem 0.7rem;
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: 3px;
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
}
.form-field select:focus { border-color: var(--accent-primary); }

.link-arrow {
  text-align: center;
  color: var(--accent-primary);
  font-size: 1.3rem;
  margin: 0.1rem 0 0.6rem;
}
.form-error { font-size: 0.8rem; color: var(--danger); margin-top: 0.5rem; }

.modal-ft {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid var(--border-subtle);
}
.btn-cancel {
  padding: 0.42rem 0.9rem;
  background: transparent;
  border: 1px solid var(--border-input);
  color: var(--text-secondary);
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.82rem;
}
.btn-cancel:hover { color: var(--text-primary); border-color: var(--text-muted); }
.btn-primary-dark {
  padding: 0.42rem 1.1rem;
  background: var(--accent-primary);
  border: none;
  color: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  transition: opacity 0.15s;
}
.btn-primary-dark:hover:not(:disabled) { opacity: 0.9; }
.btn-primary-dark:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── transitions ─────────────────────────────────────────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.2s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateX(-50%) translateY(12px); }
</style>
