<template>
  <view class="page">
    <view class="header">
      <view>
        <text class="eyebrow">我的出行</text>
        <text class="title">旅行账本</text>
      </view>
      <button class="secondary-button icon-button" @tap="loadTrips">刷新</button>
    </view>

    <button class="primary-button create-button" @tap="goCreate">创建出行</button>

    <view v-if="loading" class="empty">正在加载...</view>
    <view v-else-if="!trips.length" class="card empty">
      <text>还没有出行，先创建一个旅行账本。</text>
    </view>
    <view v-else class="trip-list">
      <view v-for="trip in trips" :key="trip.id" class="card trip-card" @tap="openTrip(trip.id)">
        <view class="trip-top">
          <text class="trip-title">{{ trip.title }}</text>
          <text class="status">{{ statusText(trip.status) }}</text>
        </view>
        <text class="muted">{{ trip.location || '未设置地点' }} · {{ dateRange(trip) }}</text>
        <view class="metrics">
          <view>
            <text class="metric-label">总额</text>
            <text class="metric-value">{{ formatMoney(trip.total_amount) }}</text>
          </view>
          <view>
            <text class="metric-label">成员</text>
            <text class="metric-value">{{ trip.member_count }}</text>
          </view>
          <view>
            <text class="metric-label">账单</text>
            <text class="metric-value">{{ trip.bill_count || trip.expense_count }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { api } from '../../utils/api';
import { dateRange, formatMoney, statusText } from '../../utils/format';

const loading = ref(false);
const trips = ref([]);

async function loadTrips() {
  loading.value = true;
  try {
    const payload = await api.listTrips();
    trips.value = payload.trips || [];
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '加载失败' });
  } finally {
    loading.value = false;
  }
}

function goCreate() {
  uni.navigateTo({ url: '/pages/trips/edit' });
}

function openTrip(tripId) {
  uni.navigateTo({ url: `/pages/trips/detail?id=${tripId}` });
}

onShow(loadTrips);
</script>

<style scoped>
.header,
.trip-top,
.metrics {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header {
  margin-bottom: 32rpx;
}

.header view {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.icon-button {
  width: 132rpx;
  line-height: 72rpx;
  font-size: 26rpx;
}

.create-button {
  margin-bottom: 28rpx;
}

.trip-list {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.trip-card {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
}

.trip-title {
  color: #18211c;
  font-size: 34rpx;
  font-weight: 800;
}

.status {
  border-radius: 999rpx;
  background: #edf4ee;
  color: #28744f;
  font-size: 22rpx;
  font-weight: 700;
  padding: 8rpx 16rpx;
}

.metrics {
  border-top: 1rpx solid #edf0eb;
  padding-top: 20rpx;
}

.metrics view {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.metric-label {
  color: #758079;
  font-size: 22rpx;
}

.metric-value {
  color: #17201b;
  font-size: 30rpx;
  font-weight: 800;
}
</style>
