<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { api } from './api';

const today = new Date().toISOString().slice(0, 10);

const sessionLoading = ref(true);
const user = ref(null);
const trips = ref([]);
const selectedTrip = ref(null);
const members = ref([]);
const expenses = ref([]);
const summary = ref(null);
const settlements = ref([]);
const authMode = ref('login');
const busy = ref('');
const message = reactive({ type: '', text: '' });

const authForm = reactive({ username: '', password: '' });
const tripForm = reactive({
  title: '',
  location: '',
  start_date: today,
  end_date: '',
  currency: 'CNY',
  note: '',
});
const editTripForm = reactive({
  title: '',
  location: '',
  start_date: '',
  end_date: '',
  currency: 'CNY',
  note: '',
});
const memberForm = reactive({ display_name: '', username: '' });
const expenseForm = reactive({
  amount: '',
  payer_id: '',
  category: '餐饮',
  spent_at: today,
  description: '',
  split_member_ids: [],
});

const isBusy = computed(() => Boolean(busy.value));
const selectedTripId = computed(() => selectedTrip.value?.id || null);
const summaryMembers = computed(() => summary.value?.members || []);
const totalAmount = computed(() => summary.value?.total || '0.00');
const perPersonAmount = computed(() => summary.value?.per_person || '0.00');
const canCreateExpense = computed(() => selectedTripId.value && members.value.length > 0 && expenseForm.payer_id);

function setMessage(type, text) {
  message.type = type;
  message.text = text;
}

function clearMessage() {
  message.type = '';
  message.text = '';
}

function setBusy(label) {
  busy.value = label;
}

function resetBusy() {
  busy.value = '';
}

function formatCurrency(value, currency = selectedTrip.value?.currency || 'CNY') {
  const amount = Number(value || 0);
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}

function formatDate(value) {
  return value || '未设置';
}

function directionText(direction) {
  if (direction === 'receivable') return '应收';
  if (direction === 'payable') return '应补';
  return '已平';
}

function directionClass(direction) {
  if (direction === 'receivable') return 'positive';
  if (direction === 'payable') return 'negative';
  return 'neutral';
}

function resetTripForm() {
  Object.assign(tripForm, {
    title: '',
    location: '',
    start_date: today,
    end_date: '',
    currency: 'CNY',
    note: '',
  });
}

function resetExpenseForm() {
  Object.assign(expenseForm, {
    amount: '',
    payer_id: members.value[0]?.id || '',
    category: '餐饮',
    spent_at: today,
    description: '',
    split_member_ids: members.value.map((member) => member.id),
  });
}

function hydrateEditTripForm(trip) {
  Object.assign(editTripForm, {
    title: trip?.title || '',
    location: trip?.location || '',
    start_date: trip?.start_date || '',
    end_date: trip?.end_date || '',
    currency: trip?.currency || 'CNY',
    note: trip?.note || '',
  });
}

async function runTask(label, task, successText = '') {
  clearMessage();
  setBusy(label);
  try {
    const result = await task();
    if (successText) setMessage('success', successText);
    return result;
  } catch (error) {
    setMessage('error', error.message || '操作失败');
    return null;
  } finally {
    resetBusy();
  }
}

async function loadSession() {
  sessionLoading.value = true;
  try {
    const payload = await api.me();
    user.value = payload.authenticated ? payload.user : null;
    if (user.value) {
      await loadTrips();
    }
  } catch (error) {
    setMessage('error', error.message || '无法连接后端服务');
  } finally {
    sessionLoading.value = false;
  }
}

async function submitAuth() {
  const action = authMode.value === 'register' ? api.register : api.login;
  const label = authMode.value === 'register' ? '注册中' : '登录中';
  const payload = await runTask(label, () => action({ ...authForm }), authMode.value === 'register' ? '注册成功' : '登录成功');
  if (!payload) return;
  user.value = payload.user;
  authForm.password = '';
  await loadTrips();
}

async function logout() {
  await runTask('退出中', api.logout);
  user.value = null;
  trips.value = [];
  selectedTrip.value = null;
  members.value = [];
  expenses.value = [];
  summary.value = null;
  settlements.value = [];
}

async function loadTrips() {
  const payload = await api.listTrips();
  trips.value = payload.trips || [];
  if (selectedTrip.value) {
    const stillSelected = trips.value.find((trip) => trip.id === selectedTrip.value.id);
    if (stillSelected) selectedTrip.value = stillSelected;
  }
}

async function createTrip() {
  const payload = await runTask(
    '创建出游',
    () => api.createTrip({ ...tripForm }),
    '出游已创建',
  );
  if (!payload) return;
  resetTripForm();
  await loadTrips();
  await selectTrip(payload.trip);
}

async function updateTrip() {
  if (!selectedTripId.value) return;
  const payload = await runTask(
    '保存出游',
    () => api.updateTrip(selectedTripId.value, { ...editTripForm }),
    '出游信息已保存',
  );
  if (!payload) return;
  selectedTrip.value = payload.trip;
  hydrateEditTripForm(payload.trip);
  await loadTrips();
}

async function deleteTrip() {
  if (!selectedTripId.value) return;
  if (!window.confirm(`确认删除「${selectedTrip.value.title}」及其账单和结算记录？`)) return;
  const deleted = await runTask('删除出游', () => api.deleteTrip(selectedTripId.value), '出游已删除');
  if (!deleted) return;
  selectedTrip.value = null;
  members.value = [];
  expenses.value = [];
  summary.value = null;
  settlements.value = [];
  await loadTrips();
}

async function selectTrip(trip) {
  selectedTrip.value = trip;
  hydrateEditTripForm(trip);
  await refreshTripData();
}

async function refreshTripData() {
  if (!selectedTripId.value) return;
  const [tripPayload, memberPayload, expensePayload, summaryPayload, settlementPayload] = await Promise.all([
    api.getTrip(selectedTripId.value),
    api.listMembers(selectedTripId.value),
    api.listExpenses(selectedTripId.value),
    api.getSummary(selectedTripId.value),
    api.listSettlements(selectedTripId.value),
  ]);
  selectedTrip.value = tripPayload.trip;
  hydrateEditTripForm(tripPayload.trip);
  members.value = memberPayload.members || [];
  expenses.value = expensePayload.expenses || [];
  summary.value = summaryPayload.summary || null;
  settlements.value = settlementPayload.settlements || [];
  if (!expenseForm.payer_id && members.value.length) {
    resetExpenseForm();
  }
}

async function addMember() {
  if (!selectedTripId.value) return;
  const payload = await runTask(
    '添加成员',
    () =>
      api.addMember(selectedTripId.value, {
        display_name: memberForm.display_name,
        username: memberForm.username,
      }),
    '成员已添加',
  );
  if (!payload) return;
  memberForm.display_name = '';
  memberForm.username = '';
  await refreshTripData();
  resetExpenseForm();
}

async function deleteMember(member) {
  if (!window.confirm(`确认删除成员「${member.display_name}」？`)) return;
  const deleted = await runTask('删除成员', () => api.deleteMember(member.id), '成员已删除');
  if (!deleted) return;
  await refreshTripData();
  resetExpenseForm();
}

function toggleSplitMember(memberId, checked) {
  if (checked) {
    if (!expenseForm.split_member_ids.includes(memberId)) {
      expenseForm.split_member_ids.push(memberId);
    }
  } else {
    expenseForm.split_member_ids = expenseForm.split_member_ids.filter((id) => id !== memberId);
  }
}

async function addExpense() {
  if (!canCreateExpense.value) return;
  const splitIds = expenseForm.split_member_ids.map((id) => Number(id)).filter(Boolean);
  if (!splitIds.length) {
    setMessage('error', '至少选择一个分摊成员');
    return;
  }
  const payload = await runTask(
    '添加账单',
    () =>
      api.addExpense(selectedTripId.value, {
        amount: expenseForm.amount,
        payer_id: Number(expenseForm.payer_id),
        category: expenseForm.category,
        spent_at: expenseForm.spent_at,
        description: expenseForm.description,
        split_member_ids: splitIds,
      }),
    '账单已添加',
  );
  if (!payload) return;
  resetExpenseForm();
  await refreshTripData();
}

async function deleteExpense(expense) {
  if (!window.confirm(`确认删除「${expense.description || expense.category}」这笔账单？`)) return;
  const deleted = await runTask('删除账单', () => api.deleteExpense(expense.id), '账单已删除');
  if (!deleted) return;
  await refreshTripData();
}

async function toggleSettlement(settlement) {
  const payload = await runTask(
    '更新结算',
    () => api.updateSettlement(settlement.id, { is_paid: !settlement.is_paid }),
    '结算状态已更新',
  );
  if (!payload) return;
  await refreshTripData();
}

async function createDemoBills() {
  if (members.value.length < 3) {
    setMessage('error', '至少需要 3 名成员才能生成 5 笔示例账单');
    return;
  }
  const [first, second, third] = members.value;
  const rows = [
    ['90.00', first.id, [first.id, second.id, third.id], '住宿', '第 1 笔：民宿押金'],
    ['60.00', second.id, [first.id, second.id, third.id], '餐饮', '第 2 笔：午餐'],
    ['30.00', third.id, [second.id, third.id], '门票', '第 3 笔：展馆门票'],
    ['45.00', first.id, [first.id, third.id], '交通', '第 4 笔：打车'],
    ['15.00', second.id, [first.id, second.id], '饮品', '第 5 笔：咖啡'],
  ];
  const created = await runTask(
    '生成示例账单',
    async () => {
      for (const [amount, payerId, splitIds, category, description] of rows) {
        await api.addExpense(selectedTripId.value, {
          amount,
          payer_id: payerId,
          split_member_ids: splitIds,
          category,
          spent_at: today,
          description,
        });
      }
      return { ok: true };
    },
    '已生成 5 笔示例账单',
  );
  if (!created) return;
  await refreshTripData();
}

onMounted(loadSession);
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">旅行账本 MVP</p>
        <h1>朋友出游记账</h1>
      </div>
      <div v-if="user" class="user-box" aria-label="当前用户">
        <span>{{ user.username }}</span>
        <button class="ghost-button" type="button" :disabled="isBusy" @click="logout">退出</button>
      </div>
    </header>

    <div v-if="message.text" class="message" :class="message.type" role="status">
      {{ message.text }}
    </div>

    <main v-if="sessionLoading" class="center-panel" aria-busy="true">
      <div class="loader" aria-hidden="true"></div>
      <p>正在连接旅行账本服务...</p>
    </main>

    <main v-else-if="!user" class="auth-layout">
      <section class="auth-copy">
        <p class="eyebrow">Trip Ledger</p>
        <h2>把每笔旅行开销算清楚</h2>
        <p>
          创建出游、添加同行成员、录入账单，系统会按 Decimal 金额自动分摊并生成结算建议。
        </p>
      </section>

      <section class="panel auth-panel" aria-labelledby="auth-title">
        <div class="segmented" role="tablist" aria-label="登录或注册">
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
          <button type="button" :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
        </div>
        <h2 id="auth-title">{{ authMode === 'login' ? '登录账号' : '创建账号' }}</h2>
        <form class="form-stack" @submit.prevent="submitAuth">
          <label>
            用户名
            <input v-model.trim="authForm.username" autocomplete="username" required />
          </label>
          <label>
            密码
            <input
              v-model="authForm.password"
              type="password"
              autocomplete="current-password"
              minlength="6"
              required
            />
          </label>
          <button class="primary-button" type="submit" :disabled="isBusy">
            {{ isBusy ? busy : authMode === 'login' ? '登录' : '注册并登录' }}
          </button>
        </form>
      </section>
    </main>

    <main v-else class="workspace">
      <aside class="panel side-panel" aria-label="我的出游">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">我的出游</p>
            <h2>行程列表</h2>
          </div>
          <button class="ghost-button" type="button" :disabled="isBusy" @click="loadTrips">刷新</button>
        </div>

        <div v-if="!trips.length" class="empty-state">
          <strong>还没有出游记录</strong>
          <p>创建一次出游后，就可以添加成员和账单。</p>
        </div>
        <div v-else class="trip-list" role="list">
          <button
            v-for="trip in trips"
            :key="trip.id"
            class="trip-item"
            :class="{ active: selectedTripId === trip.id }"
            type="button"
            @click="selectTrip(trip)"
          >
            <span>{{ trip.title }}</span>
            <small>{{ trip.location || '未设置地点' }} · {{ trip.member_count }} 人 · {{ trip.expense_count }} 笔</small>
          </button>
        </div>

        <form class="form-stack create-trip" @submit.prevent="createTrip">
          <h3>创建出游</h3>
          <label>
            名称
            <input v-model.trim="tripForm.title" placeholder="杭州三日游" required />
          </label>
          <label>
            地点
            <input v-model.trim="tripForm.location" placeholder="杭州" />
          </label>
          <div class="form-grid two">
            <label>
              开始日期
              <input v-model="tripForm.start_date" type="date" />
            </label>
            <label>
              结束日期
              <input v-model="tripForm.end_date" type="date" />
            </label>
          </div>
          <label>
            币种
            <input v-model.trim="tripForm.currency" maxlength="12" />
          </label>
          <label>
            备注
            <textarea v-model.trim="tripForm.note" rows="3" placeholder="出游说明"></textarea>
          </label>
          <button class="primary-button" type="submit" :disabled="isBusy">
            {{ busy === '创建出游' ? '创建中...' : '创建出游' }}
          </button>
        </form>
      </aside>

      <section v-if="!selectedTrip" class="panel detail-placeholder">
        <h2>选择一个出游开始记账</h2>
        <p>左侧创建或选择出游后，这里会展示成员、账单、汇总和结算建议。</p>
      </section>

      <section v-else class="detail-area" aria-label="出游详情">
        <div class="panel trip-header">
          <div>
            <p class="eyebrow">{{ selectedTrip.location || '未设置地点' }}</p>
            <h2>{{ selectedTrip.title }}</h2>
            <p>
              {{ formatDate(selectedTrip.start_date) }} 至 {{ formatDate(selectedTrip.end_date) }}
              · {{ selectedTrip.currency }}
            </p>
          </div>
          <div class="header-actions">
            <button class="ghost-button" type="button" :disabled="isBusy" @click="refreshTripData">刷新详情</button>
            <button class="danger-button" type="button" :disabled="isBusy" @click="deleteTrip">删除出游</button>
          </div>
        </div>

        <div class="metric-grid">
          <article class="metric-card">
            <span>总花费</span>
            <strong>{{ formatCurrency(totalAmount) }}</strong>
          </article>
          <article class="metric-card">
            <span>人均</span>
            <strong>{{ formatCurrency(perPersonAmount) }}</strong>
          </article>
          <article class="metric-card">
            <span>同行成员</span>
            <strong>{{ members.length }} 人</strong>
          </article>
          <article class="metric-card">
            <span>账单</span>
            <strong>{{ expenses.length }} 笔</strong>
          </article>
        </div>

        <div class="detail-grid">
          <section class="panel" aria-labelledby="trip-edit-title">
            <h3 id="trip-edit-title">基础信息</h3>
            <form class="form-stack" @submit.prevent="updateTrip">
              <label>
                名称
                <input v-model.trim="editTripForm.title" required />
              </label>
              <label>
                地点
                <input v-model.trim="editTripForm.location" />
              </label>
              <div class="form-grid two">
                <label>
                  开始日期
                  <input v-model="editTripForm.start_date" type="date" />
                </label>
                <label>
                  结束日期
                  <input v-model="editTripForm.end_date" type="date" />
                </label>
              </div>
              <label>
                备注
                <textarea v-model.trim="editTripForm.note" rows="3"></textarea>
              </label>
              <button class="secondary-button" type="submit" :disabled="isBusy">保存基础信息</button>
            </form>
          </section>

          <section class="panel" aria-labelledby="member-title">
            <div class="section-head">
              <h3 id="member-title">成员管理</h3>
              <span>{{ members.length }} 人</span>
            </div>
            <form class="inline-form" @submit.prevent="addMember">
              <label>
                昵称
                <input v-model.trim="memberForm.display_name" placeholder="Bob" required />
              </label>
              <label>
                关联用户名
                <input v-model.trim="memberForm.username" placeholder="可选" />
              </label>
              <button class="secondary-button" type="submit" :disabled="isBusy">添加</button>
            </form>
            <ul class="member-list" aria-label="成员列表">
              <li v-for="member in members" :key="member.id">
                <div>
                  <strong>{{ member.display_name }}</strong>
                  <small>{{ member.username ? `已关联 ${member.username}` : '临时昵称成员' }}</small>
                </div>
                <button class="text-button" type="button" :disabled="isBusy" @click="deleteMember(member)">删除</button>
              </li>
            </ul>
          </section>

          <section class="panel expense-panel" aria-labelledby="expense-title">
            <div class="section-head">
              <h3 id="expense-title">账单录入</h3>
              <button class="ghost-button" type="button" :disabled="isBusy || members.length < 3" @click="createDemoBills">
                生成 5 笔示例
              </button>
            </div>
            <form class="form-stack" @submit.prevent="addExpense">
              <div class="form-grid three">
                <label>
                  金额
                  <input v-model="expenseForm.amount" inputmode="decimal" placeholder="90.00" required />
                </label>
                <label>
                  付款人
                  <select v-model="expenseForm.payer_id" required>
                    <option value="" disabled>选择付款人</option>
                    <option v-for="member in members" :key="member.id" :value="member.id">
                      {{ member.display_name }}
                    </option>
                  </select>
                </label>
                <label>
                  日期
                  <input v-model="expenseForm.spent_at" type="date" required />
                </label>
              </div>
              <div class="form-grid two">
                <label>
                  分类
                  <input v-model.trim="expenseForm.category" placeholder="餐饮" />
                </label>
                <label>
                  说明
                  <input v-model.trim="expenseForm.description" placeholder="午餐、门票、打车..." />
                </label>
              </div>
              <fieldset class="checkbox-group">
                <legend>参与分摊成员</legend>
                <label v-for="member in members" :key="member.id">
                  <input
                    type="checkbox"
                    :checked="expenseForm.split_member_ids.includes(member.id)"
                    @change="toggleSplitMember(member.id, $event.target.checked)"
                  />
                  {{ member.display_name }}
                </label>
              </fieldset>
              <button class="primary-button" type="submit" :disabled="isBusy || !canCreateExpense">
                添加账单
              </button>
            </form>
          </section>

          <section class="panel wide" aria-labelledby="expense-list-title">
            <div class="section-head">
              <h3 id="expense-list-title">账单明细</h3>
              <span>{{ expenses.length }} 笔</span>
            </div>
            <div v-if="!expenses.length" class="empty-state compact">
              <strong>暂无账单</strong>
              <p>录入账单后，汇总和结算建议会自动刷新。</p>
            </div>
            <div v-else class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>说明</th>
                    <th>付款人</th>
                    <th>金额</th>
                    <th>分摊</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="expense in expenses" :key="expense.id">
                    <td>{{ expense.spent_at }}</td>
                    <td>
                      <strong>{{ expense.description || expense.category }}</strong>
                      <small>{{ expense.category }}</small>
                    </td>
                    <td>{{ expense.payer_name }}</td>
                    <td>{{ formatCurrency(expense.amount) }}</td>
                    <td>
                      <span v-for="split in expense.splits" :key="split.member_id" class="split-chip">
                        {{ split.display_name }} {{ formatCurrency(split.amount) }}
                      </span>
                    </td>
                    <td>
                      <button class="text-button danger-text" type="button" :disabled="isBusy" @click="deleteExpense(expense)">
                        删除
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="panel" aria-labelledby="summary-title">
            <div class="section-head">
              <h3 id="summary-title">成员汇总</h3>
              <span>净额 = 已付 - 应摊</span>
            </div>
            <div v-if="!summaryMembers.length" class="empty-state compact">
              <strong>暂无汇总</strong>
              <p>添加成员和账单后自动计算。</p>
            </div>
            <ul v-else class="summary-list">
              <li v-for="row in summaryMembers" :key="row.member_id">
                <div>
                  <strong>{{ row.display_name }}</strong>
                  <small>已付 {{ formatCurrency(row.paid) }} · 应摊 {{ formatCurrency(row.share) }}</small>
                </div>
                <span class="net-pill" :class="directionClass(row.direction)">
                  {{ directionText(row.direction) }} {{ formatCurrency(Math.abs(Number(row.net || 0))) }}
                </span>
              </li>
            </ul>
          </section>

          <section class="panel" aria-labelledby="settlement-title">
            <div class="section-head">
              <h3 id="settlement-title">结算建议</h3>
              <span>{{ settlements.length }} 条</span>
            </div>
            <div v-if="!settlements.length" class="empty-state compact">
              <strong>当前无需转账</strong>
              <p>所有成员已平账或还没有账单。</p>
            </div>
            <ul v-else class="settlement-list">
              <li v-for="settlement in settlements" :key="settlement.id" :class="{ paid: settlement.is_paid }">
                <div>
                  <strong>
                    {{ settlement.from_member_name }} 给 {{ settlement.to_member_name }} 转
                    {{ formatCurrency(settlement.amount) }}
                  </strong>
                  <small>{{ settlement.is_paid ? '已结清' : '待结清' }}</small>
                </div>
                <button class="secondary-button" type="button" :disabled="isBusy" @click="toggleSettlement(settlement)">
                  {{ settlement.is_paid ? '标记未结' : '标记结清' }}
                </button>
              </li>
            </ul>
          </section>
        </div>
      </section>
    </main>
  </div>
</template>
