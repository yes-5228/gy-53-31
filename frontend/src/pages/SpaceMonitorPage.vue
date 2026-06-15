<script setup>
import { computed, onMounted, ref } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import StatGrid from "../components/StatGrid.vue";
import { parkingApi } from "../api/parking";

const spaces = ref([]);
const stats = ref({});
const loading = ref(false);
const error = ref("");
const updatingId = ref(null);

const statItems = computed(() => [
  { label: "总车位", value: spaces.value.length },
  { label: "空闲", value: stats.value.free || 0 },
  { label: "占用", value: stats.value.occupied || 0 },
  { label: "预约", value: stats.value.reserved || 0 },
  { label: "维护", value: stats.value.maintenance || 0 },
]);

async function loadSpaces() {
  loading.value = true;
  error.value = "";
  try {
    const data = await parkingApi.getSpaces();
    spaces.value = data.items;
    stats.value = data.stats;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function handleStatusChange(space, event) {
  const newStatus = event.target.value;
  const oldStatus = space.status;
  if (newStatus === oldStatus) return;

  const spaceIndex = spaces.value.findIndex((s) => s.id === space.id);
  if (spaceIndex === -1) return;

  updatingId.value = space.id;
  error.value = "";

  const plate = newStatus === "occupied" ? space.plate_number || "临A00001" : null;

  try {
    await parkingApi.updateSpace(space.id, { status: newStatus, plate_number: plate });
    await loadSpaces();
  } catch (err) {
    event.target.value = oldStatus;
    error.value = `操作失败：${err.message}（${space.code} 状态已回滚）`;
  } finally {
    updatingId.value = null;
  }
}

onMounted(loadSpaces);
</script>

<template>
  <div class="page-stack">
    <header class="page-header">
      <div>
        <h2>车位状态监控</h2>
        <p>实时查看车位占用、预约和维护状态。</p>
      </div>
      <button class="primary-button" type="button" @click="loadSpaces" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </header>

    <StatGrid :stats="statItems" />
    <p v-if="error" class="error-text">{{ error }}</p>

    <div class="space-grid" :class="{ muted: loading }">
      <article v-for="space in spaces" :key="space.id" class="space-card">
        <div>
          <strong>{{ space.code }}</strong>
          <span>{{ space.area }}</span>
        </div>
        <StatusBadge :status="space.status" />
        <p>{{ space.plate_number || "无绑定车辆" }}</p>
        <select
          :value="space.status"
          :disabled="updatingId === space.id"
          @change="handleStatusChange(space, $event)"
        >
          <option value="free">空闲</option>
          <option value="occupied">占用</option>
          <option value="reserved">预约</option>
          <option value="maintenance">维护</option>
        </select>
      </article>
    </div>
  </div>
</template>
