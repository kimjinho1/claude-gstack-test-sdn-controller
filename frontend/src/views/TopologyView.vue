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
          color="#1e2d3d"
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
  await api.delete(`/device-links/${linkId}`)
  edges.value = edges.value.filter(e => e.id !== selectedEdgeId.value)
  linkMap.value.delete(`${edge.source}-${edge.target}`)
  selectedEdgeId.value = null
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
    // silently ignore duplicate on drag
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
  background: #080d12;
  position: relative;
}

/* ── toolbar ─────────────────────────────────────────────────────────────── */
.topo-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 1.1rem;
  background: #0e1520;
  border-bottom: 1px solid #1a2a3a;
  flex-shrink: 0;
  gap: 1rem;
  flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; }
.toolbar-right { display: flex; align-items: center; gap: 0.5rem; }

.topo-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: #d4dbe4;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.topo-stats { display: flex; gap: 1rem; }
.stat { font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em; }
.stat.managed { color: #0f9960; }
.stat.error   { color: #db3737; }
.stat.pending { color: #d9822b; }

.btn-tool {
  padding: 0.32rem 0.75rem;
  background: #172026;
  border: 1px solid #2a3a4a;
  color: #8fa0b4;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}
.btn-tool:hover { background: #1e2d3a; color: #d4dbe4; border-color: #3a5060; }

.btn-tool-primary {
  padding: 0.32rem 0.85rem;
  background: #1d6fa4;
  border: none;
  color: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-tool-primary:hover { background: #2585c2; }

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
  background: #080d12;
  color: #6a8099;
  font-size: 0.9rem;
}
.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid #1a2a3a;
  border-top-color: #1d6fa4;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* VueFlow overrides */
:deep(.vue-flow__background) { background: #080d12 !important; }
:deep(.vue-flow__edge-path) { stroke: #1d6fa4 !important; }
:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #48b0e4 !important;
  stroke-width: 2.5px !important;
}
:deep(.vue-flow__handle) {
  background: #1d6fa4 !important;
  border-color: #0e1520 !important;
  width: 10px !important;
  height: 10px !important;
}
:deep(.vue-flow__handle:hover) { background: #2d9de0 !important; }
:deep(.vue-flow__node.selected > *) {
  box-shadow: 0 0 0 2px #1d6fa4, 0 0 16px rgba(29,111,164,0.4) !important;
}

/* Controls dark theme */
:deep(.topo-controls) {
  background: #10192a !important;
  border: 1px solid #1e2d3a !important;
  border-radius: 4px !important;
  overflow: hidden;
}
:deep(.topo-controls button) {
  background: #10192a !important;
  color: #8fa0b4 !important;
  border-color: #1e2d3a !important;
}
:deep(.topo-controls button:hover) { background: #1a2a3a !important; color: #d4dbe4 !important; }
:deep(.topo-controls path) { fill: #8fa0b4 !important; }

/* Minimap dark */
:deep(.topo-minimap) {
  background: #0a1018 !important;
  border: 1px solid #1e2d3a !important;
  border-radius: 4px !important;
}

/* ── edge action bar ─────────────────────────────────────────────────────── */
.edge-action-bar {
  position: absolute;
  bottom: 1.2rem;
  left: 50%;
  transform: translateX(-50%);
  background: #10192a;
  border: 1px solid #2a3d4f;
  border-radius: 6px;
  padding: 0.55rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  font-size: 0.82rem;
  color: #8fa0b4;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  z-index: 50;
  white-space: nowrap;
}
.edge-action-bar strong { color: #d4dbe4; }

.btn-danger-sm {
  padding: 0.28rem 0.75rem;
  background: #3a0a0a;
  border: 1px solid #8b2222;
  color: #db3737;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 600;
  transition: all 0.15s;
}
.btn-danger-sm:hover { background: #5a1212; }
.btn-cancel-sm {
  padding: 0.28rem 0.65rem;
  background: transparent;
  border: 1px solid #2a3a4a;
  color: #6a8099;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.78rem;
}
.btn-cancel-sm:hover { color: #d4dbe4; }

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
  background: #131f2b;
  border: 1px solid #1e2d3a;
  border-radius: 6px;
  width: 380px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.7);
}
.modal-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #1e2d3a;
}
.modal-hd h3 { font-size: 0.95rem; font-weight: 700; color: #d4dbe4; margin: 0; }
.modal-close {
  background: none;
  border: none;
  color: #5c7080;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 2px 6px;
}
.modal-close:hover { color: #d4dbe4; }

.modal-bd { padding: 1.25rem; }
.form-field { margin-bottom: 0.8rem; }
.form-field label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6a8099;
  margin-bottom: 0.35rem;
}
.form-field select {
  width: 100%;
  padding: 0.5rem 0.7rem;
  background: #0e1a26;
  border: 1px solid #2a3a4a;
  border-radius: 3px;
  color: #d4dbe4;
  font-size: 0.85rem;
  outline: none;
}
.form-field select:focus { border-color: #1d6fa4; }

.link-arrow {
  text-align: center;
  color: #1d6fa4;
  font-size: 1.3rem;
  margin: 0.1rem 0 0.6rem;
}
.form-error { font-size: 0.8rem; color: #db3737; margin-top: 0.5rem; }

.modal-ft {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid #1e2d3a;
}
.btn-cancel {
  padding: 0.42rem 0.9rem;
  background: transparent;
  border: 1px solid #2a3a4a;
  color: #8fa0b4;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.82rem;
}
.btn-cancel:hover { color: #d4dbe4; border-color: #3a5060; }
.btn-primary-dark {
  padding: 0.42rem 1.1rem;
  background: #1d6fa4;
  border: none;
  color: white;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  transition: background 0.15s;
}
.btn-primary-dark:hover:not(:disabled) { background: #2585c2; }
.btn-primary-dark:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── transitions ─────────────────────────────────────────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.2s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateX(-50%) translateY(12px); }
</style>
