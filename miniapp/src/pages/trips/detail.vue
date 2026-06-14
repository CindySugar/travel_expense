<template>
  <view class="page detail-page">
    <view v-if="trip" class="hero card">
      <view>
        <text class="eyebrow">{{ trip.location || '未设置地点' }}</text>
        <text class="title">{{ trip.title }}</text>
        <text class="muted">{{ dateRange(trip) }}</text>
      </view>
      <button class="secondary-button small-button" @tap="editTrip">编辑</button>
    </view>

    <view class="metric-row">
      <view class="card metric-card">
        <text class="metric-label">总花费</text>
        <text class="metric-value">{{ formatMoney(summary?.total) }}</text>
      </view>
      <view class="card metric-card">
        <text class="metric-label">人均</text>
        <text class="metric-value">{{ formatMoney(summary?.per_person) }}</text>
      </view>
    </view>

    <view class="card section">
      <view class="section-head">
        <text class="section-title">成员</text>
        <text class="muted">{{ members.length }} 人</text>
      </view>
      <view class="member-form">
        <input class="input" v-model="memberName" placeholder="成员昵称" />
        <button class="secondary-button add-button" @tap="addMember">添加</button>
      </view>
      <view v-if="!members.length" class="empty">暂无成员</view>
      <view v-else class="member-list">
        <view v-for="member in members" :key="member.id" class="member-row">
          <text>{{ member.display_name }}</text>
          <button class="link danger-link" @tap="deleteMember(member)">删除</button>
        </view>
      </view>
    </view>

    <view class="card section">
      <view class="section-head">
        <text class="section-title">账单</text>
        <button class="secondary-button small-button" @tap="addExpense">新增</button>
      </view>
      <view v-if="!expenses.length" class="empty">暂无账单</view>
      <view v-else class="expense-list">
        <view v-for="expense in expenses" :key="expense.id" class="expense-row">
          <view>
            <text class="expense-title">{{ expense.description || expense.category }}</text>
            <text class="muted">{{ expense.spent_at }} · {{ expense.payer_name }} 付款</text>
          </view>
          <view class="expense-side">
            <text class="expense-money">{{ formatMoney(expense.amount) }}</text>
            <button class="link danger-link" @tap="deleteExpense(expense)">删除</button>
          </view>
        </view>
      </view>
    </view>

    <view class="card section">
      <view class="section-head">
        <text class="section-title">成员汇总</text>
      </view>
      <view v-if="!summaryMembers.length" class="empty">暂无汇总</view>
      <view v-else class="summary-list">
        <view v-for="row in summaryMembers" :key="row.member_id" class="summary-row">
          <view>
            <text class="expense-title">{{ row.display_name }}</text>
            <text class="muted">已付 {{ formatMoney(row.paid) }} · 应摊 {{ formatMoney(row.share) }}</text>
          </view>
          <text :class="['net', row.direction]">{{ directionText(row) }}</text>
        </view>
      </view>
    </view>

    <view class="card section">
      <view class="section-head">
        <text class="section-title">结算建议</text>
      </view>
      <view v-if="!settlements.length" class="empty">当前无需转账</view>
      <view v-else class="settlement-list">
        <view v-for="settlement in settlements" :key="settlement.id" class="settlement-row">
          <view>
            <text class="expense-title">
              {{ settlement.from_member_name }} 转 {{ settlement.to_member_name }}
            </text>
            <text class="muted">{{ formatMoney(settlement.amount) }} · {{ settlement.is_paid ? '已结清' : '待结清' }}</text>
          </view>
          <button class="secondary-button settle-button" @tap="toggleSettlement(settlement)">
            {{ settlement.is_paid ? '撤销' : '结清' }}
          </button>
        </view>
      </view>
    </view>

    <button class="danger-button" @tap="deleteTrip">删除出行</button>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { api } from '../../utils/api';
import { dateRange, formatMoney } from '../../utils/format';

const tripId = ref('');
const trip = ref(null);
const members = ref([]);
const expenses = ref([]);
const summary = ref(null);
const settlements = ref([]);
const memberName = ref('');

const summaryMembers = computed(() => summary.value?.members || []);

async function loadAll() {
  if (!tripId.value) return;
  try {
    const [tripPayload, memberPayload, expensePayload, summaryPayload, settlementPayload] = await Promise.all([
      api.getTrip(tripId.value),
      api.listMembers(tripId.value),
      api.listExpenses(tripId.value),
      api.getSummary(tripId.value),
      api.listSettlements(tripId.value),
    ]);
    trip.value = tripPayload.trip;
    members.value = memberPayload.members || [];
    expenses.value = expensePayload.expenses || [];
    summary.value = summaryPayload.summary || null;
    settlements.value = settlementPayload.settlements || [];
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '加载失败' });
  }
}

function editTrip() {
  uni.navigateTo({ url: `/pages/trips/edit?id=${tripId.value}` });
}

function addExpense() {
  if (!members.value.length) {
    uni.showToast({ icon: 'none', title: '请先添加成员' });
    return;
  }
  uni.navigateTo({ url: `/pages/expenses/edit?tripId=${tripId.value}` });
}

async function addMember() {
  const displayName = memberName.value.trim();
  if (!displayName) {
    uni.showToast({ icon: 'none', title: '请填写成员昵称' });
    return;
  }
  try {
    await api.addMember(tripId.value, { display_name: displayName });
    memberName.value = '';
    await loadAll();
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '添加失败' });
  }
}

function confirmAction(content, onConfirm) {
  uni.showModal({
    title: '请确认',
    content,
    success(result) {
      if (result.confirm) onConfirm();
    },
  });
}

function deleteMember(member) {
  confirmAction(`删除成员 ${member.display_name}？`, async () => {
    try {
      await api.deleteMember(member.id);
      await loadAll();
    } catch (error) {
      uni.showToast({ icon: 'none', title: error.message || '删除失败' });
    }
  });
}

function deleteExpense(expense) {
  confirmAction(`删除账单 ${expense.description || expense.category}？`, async () => {
    try {
      await api.deleteExpense(expense.id);
      await loadAll();
    } catch (error) {
      uni.showToast({ icon: 'none', title: error.message || '删除失败' });
    }
  });
}

function deleteTrip() {
  confirmAction('删除该出行及其全部账单？', async () => {
    try {
      await api.deleteTrip(tripId.value);
      uni.reLaunch({ url: '/pages/trips/index' });
    } catch (error) {
      uni.showToast({ icon: 'none', title: error.message || '删除失败' });
    }
  });
}

async function toggleSettlement(settlement) {
  try {
    await api.updateSettlement(settlement.id, { is_paid: !settlement.is_paid });
    await loadAll();
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '更新失败' });
  }
}

function directionText(row) {
  const amount = formatMoney(Math.abs(Number(row.net || 0)));
  if (row.direction === 'receivable') return `应收 ${amount}`;
  if (row.direction === 'payable') return `应补 ${amount}`;
  return '已平';
}

onLoad((query) => {
  tripId.value = query.id || '';
});

onShow(loadAll);
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.hero,
.section-head,
.member-row,
.expense-row,
.summary-row,
.settlement-row,
.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.hero view {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.small-button {
  width: 124rpx;
  line-height: 70rpx;
  font-size: 26rpx;
}

.metric-row {
  align-items: stretch;
}

.metric-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.metric-label,
.muted {
  color: #6b7670;
  font-size: 24rpx;
}

.metric-value {
  color: #17201b;
  font-size: 34rpx;
  font-weight: 800;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.section-title {
  color: #17201b;
  font-size: 32rpx;
  font-weight: 800;
}

.member-form {
  display: flex;
  gap: 16rpx;
}

.member-form .input {
  flex: 1;
}

.add-button {
  width: 126rpx;
  line-height: 84rpx;
  font-size: 26rpx;
}

.member-list,
.expense-list,
.summary-list,
.settlement-list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.member-row,
.expense-row,
.summary-row,
.settlement-row {
  border-top: 1rpx solid #eef1ed;
  padding-top: 18rpx;
}

.expense-row view,
.summary-row view,
.settlement-row view {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8rpx;
}

.expense-title {
  color: #17201b;
  font-size: 29rpx;
  font-weight: 750;
}

.expense-side {
  align-items: flex-end;
  flex: none !important;
}

.expense-money,
.net {
  color: #17201b;
  font-size: 28rpx;
  font-weight: 800;
}

.net.receivable {
  color: #1f7a4d;
}

.net.payable {
  color: #b44a2b;
}

.net.settled {
  color: #6b7670;
}

.link {
  background: transparent;
  color: #28744f;
  font-size: 24rpx;
  line-height: 42rpx;
  padding: 0;
}

.danger-link {
  color: #a9362b;
}

.settle-button {
  width: 112rpx;
  line-height: 66rpx;
  font-size: 25rpx;
}
</style>
