<template>
  <div class="tree">
    <div class="tree-header">
      <span>네트워크 토폴로지</span>
      <button v-if="auth.isAdmin" class="btn-add" @click="showAddGroup = true" title="그룹 추가">+</button>
    </div>

    <div v-if="loading" class="loading">로딩 중...</div>

    <div v-for="group in groups" :key="group.id" class="group">
      <div class="group-header" @click="toggleGroup(group.id)">
        <span class="arrow">{{ expanded.groups.has(group.id) ? "▼" : "▶" }}</span>
        <span class="label">{{ group.name }}</span>
        <button v-if="auth.isAdmin" class="btn-small" @click.stop="addSite(group)" title="사이트 추가">+</button>
      </div>

      <div v-if="expanded.groups.has(group.id)">
        <div v-for="site in group.sites" :key="site.id" class="site">
          <div
            class="site-header"
            :class="{ active: selectedSiteId === site.id }"
            @click="selectSite(site)"
          >
            <span class="arrow" @click.stop="toggleSite(site.id)">
              {{ expanded.sites.has(site.id) ? "▼" : "▶" }}
            </span>
            <span class="label">{{ site.name }}</span>
            <button v-if="auth.isAdmin" class="btn-small" @click.stop="addBuilding(site)" title="건물 추가">+</button>
          </div>

          <div v-if="expanded.sites.has(site.id)">
            <div
              v-for="building in site.buildings"
              :key="building.id"
              class="building"
              :class="{ active: selectedBuildingId === building.id }"
              @click="selectBuilding(building, site)"
            >
              <span class="label">{{ building.name }}</span>
              <span class="count">{{ building.device_count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Group Modal -->
    <div v-if="showAddGroup" class="modal-overlay" @click.self="showAddGroup = false">
      <div class="modal">
        <h3>그룹 추가</h3>
        <input v-model="newName" placeholder="그룹 이름" @keyup.enter="createGroup" />
        <div class="modal-actions">
          <button @click="createGroup">추가</button>
          <button class="cancel" @click="showAddGroup = false">취소</button>
        </div>
      </div>
    </div>

    <!-- Add Site Modal -->
    <div v-if="addSiteTarget" class="modal-overlay" @click.self="addSiteTarget = null">
      <div class="modal">
        <h3>사이트 추가 — {{ addSiteTarget.name }}</h3>
        <input v-model="newName" placeholder="사이트 이름" @keyup.enter="createSite" />
        <div class="modal-actions">
          <button @click="createSite">추가</button>
          <button class="cancel" @click="addSiteTarget = null">취소</button>
        </div>
      </div>
    </div>

    <!-- Add Building Modal -->
    <div v-if="addBuildingTarget" class="modal-overlay" @click.self="addBuildingTarget = null">
      <div class="modal">
        <h3>건물 추가 — {{ addBuildingTarget.site.name }}</h3>
        <input v-model="newName" placeholder="건물 이름" />
        <input v-model.number="newFloors" type="number" placeholder="층수" min="1" style="margin-top: 0.5rem;" />
        <div class="modal-actions">
          <button @click="createBuilding">추가</button>
          <button class="cancel" @click="addBuildingTarget = null">취소</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useTopologyStore, type Group, type Site } from "@/stores/topology";

const emit = defineEmits<{
  (e: "select", payload: { siteId?: number; buildingId?: number }): void;
}>();

const auth = useAuthStore();
const topologyStore = useTopologyStore();

const groups = computed(() => topologyStore.groups);
const loading = computed(() => topologyStore.loading);

const expanded = reactive({ groups: new Set<number>(), sites: new Set<number>() });
const selectedSiteId = ref<number | undefined>();
const selectedBuildingId = ref<number | undefined>();

const showAddGroup = ref(false);
const addSiteTarget = ref<Group | null>(null);
const addBuildingTarget = ref<{ site: Site } | null>(null);
const newName = ref("");
const newFloors = ref(1);

function toggleGroup(id: number) {
  expanded.groups.has(id) ? expanded.groups.delete(id) : expanded.groups.add(id);
}
function toggleSite(id: number) {
  expanded.sites.has(id) ? expanded.sites.delete(id) : expanded.sites.add(id);
}

function selectSite(site: Site) {
  selectedSiteId.value = site.id;
  selectedBuildingId.value = undefined;
  expanded.sites.add(site.id);
  emit("select", { siteId: site.id });
}

function selectBuilding(building: any, site: Site) {
  selectedSiteId.value = site.id;
  selectedBuildingId.value = building.id;
  emit("select", { siteId: site.id, buildingId: building.id });
}

function addSite(group: Group) { addSiteTarget.value = group; newName.value = ""; }
function addBuilding(site: Site) { addBuildingTarget.value = { site }; newName.value = ""; newFloors.value = 1; }

async function createGroup() {
  if (!newName.value.trim()) return;
  await topologyStore.createGroup(newName.value.trim());
  showAddGroup.value = false;
  newName.value = "";
}

async function createSite() {
  if (!addSiteTarget.value || !newName.value.trim()) return;
  const site = await topologyStore.createSite(addSiteTarget.value.id, newName.value.trim());
  expanded.groups.add(addSiteTarget.value.id);
  addSiteTarget.value = null;
  newName.value = "";
}

async function createBuilding() {
  if (!addBuildingTarget.value || !newName.value.trim()) return;
  await topologyStore.createBuilding(addBuildingTarget.value.site.id, newName.value.trim(), newFloors.value);
  addBuildingTarget.value = null;
  newName.value = "";
}
</script>

<style scoped>
.tree { padding: 0.75rem 0; }
.tree-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600;
  color: #718096; text-transform: uppercase; letter-spacing: 0.05em;
}
.btn-add {
  background: #4299e1; color: white; border: none; border-radius: 4px;
  width: 20px; height: 20px; cursor: pointer; font-size: 1rem; line-height: 1;
}
.group-header, .site-header {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.45rem 1rem; cursor: pointer; user-select: none;
}
.group-header:hover, .site-header:hover { background: #f7fafc; }
.site-header.active { background: #ebf8ff; color: #2b6cb0; }
.arrow { font-size: 0.65rem; color: #a0aec0; min-width: 12px; }
.label { flex: 1; font-size: 0.9rem; }
.group-header .label { font-weight: 600; }
.btn-small {
  background: none; border: 1px solid #e2e8f0; border-radius: 3px;
  width: 18px; height: 18px; cursor: pointer; font-size: 0.8rem; color: #718096;
  display: flex; align-items: center; justify-content: center;
}
.btn-small:hover { background: #ebf8ff; border-color: #4299e1; color: #4299e1; }
.site { padding-left: 1rem; }
.building {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.35rem 1rem 0.35rem 1.5rem; cursor: pointer; font-size: 0.875rem;
}
.building:hover { background: #f7fafc; }
.building.active { background: #ebf8ff; color: #2b6cb0; font-weight: 500; }
.count {
  background: #e2e8f0; color: #4a5568; border-radius: 10px;
  padding: 0.1rem 0.5rem; font-size: 0.75rem;
}
.loading { padding: 1rem; color: #718096; font-size: 0.9rem; text-align: center; }
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 200;
}
.modal {
  background: white; border-radius: 8px; padding: 1.5rem;
  width: 320px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}
.modal h3 { margin-bottom: 1rem; font-size: 1rem; }
.modal input {
  width: 100%; padding: 0.5rem 0.7rem; border: 1px solid #e2e8f0;
  border-radius: 6px; font-size: 0.9rem; outline: none;
}
.modal input:focus { border-color: #4299e1; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1rem; justify-content: flex-end; }
.modal-actions button {
  padding: 0.4rem 1rem; border: none; border-radius: 6px;
  cursor: pointer; font-size: 0.9rem; background: #4299e1; color: white;
}
.modal-actions button.cancel { background: #e2e8f0; color: #4a5568; }
</style>
