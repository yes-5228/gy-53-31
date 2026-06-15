<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { parkingApi } from "../api/parking";
import StatusBadge from "../components/StatusBadge.vue";

const spaces = ref([]);
const orders = ref([]);
const message = ref("");
const messageType = ref("info");
const quote = ref(null);
const releasing = ref(false);
const entryForm = reactive({
  plate_number: "",
  space_code: "",
});
const calcForm = reactive({
  entry_time: new Date(Date.now() - 90 * 60 * 1000).toISOString().slice(0, 16),
  exit_time: new Date().toISOString().slice(0, 16),
});

const freeSpaces = computed(() => spaces.value.filter((space) => ["free", "reserved"].includes(space.status)));
const parkingOrders = computed(() => orders.value.filter((order) => order.status === "parking"));

const pendingReleaseOrders = computed(() => {
  const spaceMap = new Map(spaces.value.map((s) => [s.code, s]));
  return orders.value.filter((order) => {
    if (order.status !== "paid") return false;
    const space = spaceMap.get(order.space_code);
    return space && space.status === "occupied";
  });
});

function showMsg(text, type = "info") {
  message.value = text;
  messageType.value = type;
}

async function loadData() {
  const [spaceData, orderData] = await Promise.all([parkingApi.getSpaces(), parkingApi.getOrders()]);
  spaces.value = spaceData.items;
  orders.value = orderData.items;
  if (!entryForm.space_code && freeSpaces.value[0]) entryForm.space_code = freeSpaces.value[0].code;
}

async function createEntry() {
  showMsg("");
  try {
    await parkingApi.entry(entryForm);
    entryForm.plate_number = "";
    await loadData();
    showMsg("入场登记成功", "success");
  } catch (err) {
    showMsg(err.message, "error");
  }
}

async function calculate() {
  quote.value = await parkingApi.calculate(calcForm);
}

async function closeOrder(order) {
  showMsg("");
  try {
    const result = await parkingApi.exit(order.id, { exit_time: new Date().toISOString().slice(0, 16) });
    showMsg(`${order.plate_number} 已结算，金额 ¥${result.amount}，请确认后释放车位`, "success");
    await loadData();
  } catch (err) {
    showMsg(err.message, "error");
  }
}

async function releaseOrder(order) {
  if (releasing.value) return;
  releasing.value = true;
  showMsg("");
  try {
    await parkingApi.releaseSpace(order.id);
    showMsg(`${order.plate_number} 车位已释放`, "success");
    await loadData();
  } catch (err) {
    showMsg(`释放失败：${err.message}`, "error");
  } finally {
    releasing.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div class="page-stack">
    <header class="page-header">
      <div>
        <h2>临时停车计费</h2>
        <p>登记入场、试算费用、结算并释放车位。</p>
      </div>
    </header>

    <div class="billing-grid">
      <form class="form-panel" @submit.prevent="createEntry">
        <h3>车辆入场</h3>
        <label>车牌号<input v-model="entryForm.plate_number" required /></label>
        <label>
          车位
          <select v-model="entryForm.space_code" required>
            <option v-for="space in freeSpaces" :key="space.id" :value="space.code">{{ space.code }}</option>
          </select>
        </label>
        <button class="primary-button" type="submit">登记入场</button>
        <p v-if="message" :class="['hint-text', `text-${messageType}`]">{{ message }}</p>
      </form>

      <form class="form-panel" @submit.prevent="calculate">
        <h3>费用试算</h3>
        <label>入场时间<input v-model="calcForm.entry_time" type="datetime-local" required /></label>
        <label>离场时间<input v-model="calcForm.exit_time" type="datetime-local" required /></label>
        <button class="secondary-button" type="submit">计算费用</button>
        <p v-if="quote" class="quote-text">停车 {{ quote.duration_hours }} 小时，应收 ¥{{ quote.amount }}</p>
      </form>
    </div>

    <section class="table-section">
      <h3>在场车辆 ({{ parkingOrders.length }})</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>订单</th>
              <th>车牌</th>
              <th>车位</th>
              <th>入场时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in parkingOrders" :key="order.id">
              <td>#{{ order.id }}</td>
              <td>{{ order.plate_number }}</td>
              <td>{{ order.space_code }}</td>
              <td>{{ order.entry_time }}</td>
              <td><StatusBadge :status="order.status" /></td>
              <td><button class="small-button" type="button" @click="closeOrder(order)">离场结算</button></td>
            </tr>
            <tr v-if="parkingOrders.length === 0">
              <td colspan="6" class="empty-cell">暂无在场车辆</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="table-section" v-if="pendingReleaseOrders.length > 0">
      <h3>待释放车位 ({{ pendingReleaseOrders.length }})</h3>
      <p class="section-hint">订单已结算，确认无误后点击「释放车位」将车位恢复为空闲。</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>订单</th>
              <th>车牌</th>
              <th>车位</th>
              <th>入场时间</th>
              <th>离场时间</th>
              <th>金额</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in pendingReleaseOrders" :key="order.id">
              <td>#{{ order.id }}</td>
              <td>{{ order.plate_number }}</td>
              <td>{{ order.space_code }}</td>
              <td>{{ order.entry_time }}</td>
              <td>{{ order.exit_time }}</td>
              <td>¥{{ order.amount }}</td>
              <td><StatusBadge :status="order.status" /></td>
              <td>
                <button
                  class="small-button primary-button"
                  type="button"
                  :disabled="releasing"
                  @click="releaseOrder(order)"
                >
                  {{ releasing ? '释放中...' : '释放车位' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
