<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { api } from './api';

const today = new Date().toISOString().slice(0, 10);
const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  minimumFractionDigits: 2,
});

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
const message = reactive({ type: '', text: '', leaving: false });
let messageHideTimer = null;
let messageClearTimer = null;

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

const isBusy = computed(() => Boolean(busy.value));
const selectedTripId = computed(() => selectedTrip.value?.id || null);
const summaryMembers = computed(() => summary.value?.members || []);
const totalAmount = computed(() => summary.value?.total || '0.00');
const perPersonAmount = computed(() => summary.value?.per_person || '0.00');

function stopMessageTimers() {
  if (messageHideTimer) {
    window.clearTimeout(messageHideTimer);
    messageHideTimer = null;
  }
  if (messageClearTimer) {
    window.clearTimeout(messageClearTimer);
    messageClearTimer = null;
  }
}

function fadeMessage() {
  if (!message.text) return;
  message.leaving = true;
  messageClearTimer = window.setTimeout(() => {
    message.type = '';
    message.text = '';
    message.leaving = false;
    messageClearTimer = null;
  }, 300);
}

function setMessage(type, text, autoHide = type === 'success') {
  stopMessageTimers();
  message.type = type;
  message.text = text;
  message.leaving = false;
  if (autoHide) {
    messageHideTimer = window.setTimeout(() => {
      messageHideTimer = null;
      fadeMessage();
    }, 3000);
  }
}

function clearMessage() {
  stopMessageTimers();
  message.type = '';
  message.text = '';
  message.leaving = false;
}

function setBusy(label) {
  busy.value = label;
}

function resetBusy() {
  busy.value = '';
}

function formatCurrency(value) {
  const amount = Number(value || 0);
  return currencyFormatter.format(Number.isFinite(amount) ? amount : 0);
}

function formatDate(value) {
  if (!value) return '未设置';
  return value;
}

function formatUpdatedLine(value) {
  if (!value) return '更新时间未知';
  return `${value.slice(0, 10)} 更新`;
}

function splitDateRange(trip) {
  const start = trip.start_date || '';
  const end = trip.end_date || '';
  if (start && end) return `${start} - ${end}`;
  if (start) return start;
  if (end) return end;
  return '未设置日期';
}

function tripDateLabel(trip) {
  return trip.end_date ? `${formatDate(trip.start_date)} 至 ${formatDate(trip.end_date)}` : formatDate(trip.start_date);
}

function avatarHue(seed) {
  const text = String(seed || '');
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 31 + text.charCodeAt(index)) % 360;
  }
  return hash;
}

function avatarStyle(name, index) {
  const hue = (avatarHue(name) + index * 47) % 360;
  return {
    backgroundColor: `hsl(${hue} 62% 68%)`,
    color: 'rgba(18, 24, 30, 0.9)',
  };
}

function avatarLabel(name) {
  const value = String(name || '').trim();
  if (!value) return '?';
  const parts = value.split(/\s+/).filter(Boolean);
  if (parts.length > 1) {
    return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase();
  }
  return value.slice(0, 2).toUpperCase();
}

function statusLabel(status) {
  if (status === 'planned') return '未出发';
  if (status === 'completed') return '已结束';
  if (status === 'ongoing') return '进行中';
  return '草稿';
}

function statusClass(status) {
  if (status === 'planned') return 'status planned';
  if (status === 'completed') return 'status completed';
  if (status === 'ongoing') return 'status ongoing';
  return 'status draft';
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

function normalizeTrip(trip) {
  if (!trip) return null;
  return {
    ...trip,
    member_count: Number(trip.member_count || 0),
    expense_count: Number(trip.expense_count || 0),
    total_amount: trip.total_amount || '0.00',
    bill_count: Number(trip.bill_count || trip.expense_count || 0),
    status: trip.status || 'draft',
    last_updated_at: trip.last_updated_at || trip.updated_at || '',
  };
}

function applyTripSelection(trip) {
  const normalized = normalizeTrip(trip);
  selectedTrip.value = normalized;
  hydrateEditTripForm(normalized);
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
  const nextTrips = (payload.trips || []).map(normalizeTrip);
  const tripsWithMembers = await Promise.all(
    nextTrips.map(async (trip) => {
      try {
        const memberPayload = await api.listMembers(trip.id);
        return {
          ...trip,
          members_preview: (memberPayload.members || []).slice(0, 4),
        };
      } catch (error) {
        return {
          ...trip,
          members_preview: [],
        };
      }
    }),
  );
  trips.value = tripsWithMembers;
  if (selectedTrip.value) {
    const stillSelected = tripsWithMembers.find((trip) => trip.id === selectedTrip.value.id);
    if (stillSelected) {
      selectedTrip.value = stillSelected;
    } else {
      selectedTrip.value = null;
      members.value = [];
      expenses.value = [];
      summary.value = null;
      settlements.value = [];
    }
  }
}

async function createTrip() {
  const payload = await runTask('创建中', () => api.createTrip({ ...tripForm }), '已创建出行');
  if (!payload) return;
  resetTripForm();
  await loadTrips();
  await openTrip(payload.trip);
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
  applyTripSelection(tripPayload.trip);
  members.value = memberPayload.members || [];
  expenses.value = expensePayload.expenses || [];
  summary.value = summaryPayload.summary || null;
  settlements.value = settlementPayload.settlements || [];
  const payerStillExists = members.value.some((member) => member.id === Number(expenseForm.payer_id));
  if (!payerStillExists) {
    resetExpenseForm();
  }
}

async function openTrip(trip) {
  applyTripSelection(trip);
  await refreshTripData();
}

async function updateTrip() {
  if (!selectedTripId.value) return;
  const payload = await runTask('保存中', () => api.updateTrip(selectedTripId.value, { ...editTripForm }), '已保存出行信息');
  if (!payload) return;
  applyTripSelection(payload.trip);
  await loadTrips();
}

async function deleteTrip() {
  if (!selectedTripId.value) return;
  if (!window.confirm(`确认删除「${selectedTrip.value.title}」以及其账单和结算记录？`)) return;
  const deleted = await runTask('删除中', () => api.deleteTrip(selectedTripId.value), '已删除出行');
  if (!deleted) return;
  selectedTrip.value = null;
  members.value = [];
  expenses.value = [];
  summary.value = null;
  settlements.value = [];
  await loadTrips();
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
}

async function deleteMember(member) {
  if (!window.confirm(`确认删除成员「${member.display_name}」？`)) return;
  const deleted = await runTask('删除成员', () => api.deleteMember(member.id), '成员已删除');
  if (!deleted) return;
  await refreshTripData();
}

const memberForm = reactive({ display_name: '', username: '' });
const expenseForm = reactive({
  amount: '',
  payer_id: '',
  category: '餐饮',
  spent_at: today,
  description: '',
  split_member_ids: [],
});

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

function toggleSplitMember(memberId, checked) {
  if (checked) {
    if (!expenseForm.split_member_ids.includes(memberId)) {
      expenseForm.split_member_ids.push(memberId);
    }
  } else {
    expenseForm.split_member_ids = expenseForm.split_member_ids.filter((id) => id !== memberId);
  }
}

const canCreateExpense = computed(() => selectedTripId.value && members.value.length > 0 && expenseForm.payer_id);

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
  if (!window.confirm(`确认删除账单「${expense.description || expense.category}」？`)) return;
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
    setMessage('error', '至少需要 3 名成员才能生成示例账单');
    return;
  }
  const [first, second, third] = members.value;
  const rows = [
    ['90.00', first.id, [first.id, second.id, third.id], '住宿', '示例 1: 民宿押金'],
    ['60.00', second.id, [first.id, second.id, third.id], '餐饮', '示例 2: 午餐'],
    ['30.00', third.id, [second.id, third.id], '门票', '示例 3: 展馆门票'],
    ['45.00', first.id, [first.id, third.id], '交通', '示例 4: 打车'],
    ['15.00', second.id, [first.id, second.id], '饮品', '示例 5: 咖啡'],
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

function tripDisplayMembers(trip) {
  if (Array.isArray(trip.members_preview) && trip.members_preview.length) {
    return trip.members_preview;
  }
  if (Array.isArray(trip.members) && trip.members.length) {
    return trip.members;
  }
  return [];
}

onMounted(loadSession);
onUnmounted(stopMessageTimers);
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand-copy">
        <p class="eyebrow">旅行账本</p>
        <h1>朋友出游记账</h1>
      </div>
      <div v-if="user" class="user-box" aria-label="当前用户">
        <span class="username" :title="user.username">{{ user.username }}</span>
        <button class="ghost-button logout-button" type="button" :disabled="isBusy" @click="logout">退出</button>
      </div>
    </header>

    <div v-if="message.text" class="message" :class="[message.type, { leaving: message.leaving }]" role="status">
      {{ message.text }}
    </div>

    <main v-if="sessionLoading" class="center-panel" aria-busy="true">
      <div class="loader" aria-hidden="true"></div>
      <p>正在连接旅行账本服务...</p>
    </main>

    <main v-else-if="!user" class="auth-layout">
      <section class="auth-copy">
        <p class="eyebrow">Trip Ledger</p>
        <h2>把每一笔旅行开销算清楚</h2>
        <p>创建出行、添加成员、录入账单，系统会自动生成分摊结果和结算建议。</p>
      </section>

      <section class="panel auth-panel" aria-labelledby="auth-title">
        <div class="segmented" role="tablist" aria-label="登录或注册">
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">登录</button>
          <button type="button" :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
        </div>
        <h2 id="auth-title">{{ authMode === 'login' ? '登录账户' : '创建账户' }}</h2>
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
      <section class="panel side-panel" aria-label="出行列表">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">我的出行</p>
            <h2>创建或浏览</h2>
          </div>
          <button class="ghost-button" type="button" :disabled="isBusy" @click="loadTrips">刷新</button>
        </div>

        <form class="form-stack create-trip" @submit.prevent="createTrip">
          <h3>创建出行 / 群组</h3>
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
            <textarea v-model.trim="tripForm.note" rows="3" placeholder="出行说明"></textarea>
          </label>
          <button class="primary-button" type="submit" :disabled="isBusy">
            {{ busy === '创建中' ? '创建中...' : '创建出行' }}
          </button>
        </form>

        <div v-if="!trips.length" class="empty-state">
          <strong>还没有出行</strong>
          <p>先创建一个群组或旅行，之后就能进入详情页管理成员和账单。</p>
        </div>

        <div v-else class="trip-list" role="list">
          <button
            v-for="trip in trips"
            :key="trip.id"
            class="trip-card"
            :class="{ active: selectedTripId === trip.id }"
            type="button"
            @click="openTrip(trip)"
          >
            <div class="trip-card__top">
              <div class="trip-card__title">
                <strong>{{ trip.title }}</strong>
                <span class="status-pill" :class="statusClass(trip.status)">{{ statusLabel(trip.status) }}</span>
              </div>
              <p class="trip-card__date">{{ tripDateLabel(trip) }}</p>
            </div>

            <div class="trip-card__metrics">
              <div>
                <span>总额</span>
                <strong>{{ formatCurrency(trip.total_amount) }}</strong>
              </div>
              <div>
                <span>成员</span>
                <strong>{{ trip.member_count }}</strong>
              </div>
              <div>
                <span>账单</span>
                <strong>{{ trip.bill_count }}</strong>
              </div>
            </div>

            <div class="trip-card__avatars" aria-label="成员头像">
              <span
                v-for="(member, index) in tripDisplayMembers(trip).slice(0, 4)"
                :key="member.id || `${trip.id}-${index}`"
                class="avatar"
                :style="avatarStyle(member.display_name || member.username || trip.title, index)"
                :title="member.display_name || member.username || trip.title"
              >
                {{ avatarLabel(member.display_name || member.username || trip.title) }}
              </span>
              <span v-if="trip.member_count > 4" class="avatar more">+{{ trip.member_count - 4 }}</span>
            </div>

            <p class="trip-card__updated">{{ formatUpdatedLine(trip.last_updated_at) }}</p>
          </button>
        </div>
      </section>

      <section v-if="!selectedTrip" class="panel detail-placeholder">
        <h2>点击一个出行卡片查看详情</h2>
        <p>详情页会提供成员、账单和结算操作；首页只保留创建与浏览。</p>
      </section>

      <section v-else class="detail-area" aria-label="出行详情">
        <div class="panel trip-header">
          <div>
            <p class="eyebrow">{{ selectedTrip.location || '未设置地点' }}</p>
            <h2>{{ selectedTrip.title }}</h2>
            <p>
              {{ splitDateRange(selectedTrip) }} · {{ selectedTrip.currency }} ·
              {{ formatUpdatedLine(selectedTrip.last_updated_at) }}
            </p>
          </div>
          <div class="header-actions">
            <button class="ghost-button" type="button" :disabled="isBusy" @click="refreshTripData">刷新详情</button>
            <button class="danger-button" type="button" :disabled="isBusy" @click="deleteTrip">删除出行</button>
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
            <span>成员</span>
            <strong>{{ members.length }} 人</strong>
          </article>
          <article class="metric-card">
            <span>账单</span>
            <strong>{{ expenses.length }} 笔</strong>
          </article>
        </div>

        <div class="detail-grid">
          <section class="panel" aria-labelledby="trip-edit-title">
            <h3 id="trip-edit-title">出行信息</h3>
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
              <button class="secondary-button" type="submit" :disabled="isBusy">保存出行信息</button>
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
                <div class="member-meta">
                  <span class="member-avatar" :style="avatarStyle(member.display_name || member.username, member.id)">
                    {{ avatarLabel(member.display_name || member.username) }}
                  </span>
                  <div>
                    <strong>{{ member.display_name }}</strong>
                    <small>{{ member.username ? `已关联 ${member.username}` : '临时昵称成员' }}</small>
                  </div>
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
              <p>录入账单后，汇总和结算建议会自动更新。</p>
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
              <p>所有成员已平或还没有账单。</p>
            </div>
            <ul v-else class="settlement-list">
              <li v-for="settlement in settlements" :key="settlement.id" :class="{ paid: settlement.is_paid }">
                <div>
                  <strong>
                    {{ settlement.from_member_name }} 转 {{ settlement.to_member_name }}
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
