<template>
  <view class="page form-page">
    <view class="field">
      <text>名称</text>
      <input class="input" v-model="form.title" placeholder="杭州三日游" />
    </view>
    <view class="field">
      <text>地点</text>
      <input class="input" v-model="form.location" placeholder="杭州" />
    </view>
    <view class="field">
      <text>开始日期</text>
      <picker mode="date" :value="form.start_date" @change="form.start_date = $event.detail.value">
        <view class="picker-value">{{ form.start_date || '选择日期' }}</view>
      </picker>
    </view>
    <view class="field">
      <text>结束日期</text>
      <picker mode="date" :value="form.end_date" @change="form.end_date = $event.detail.value">
        <view class="picker-value">{{ form.end_date || '选择日期' }}</view>
      </picker>
    </view>
    <view class="field">
      <text>币种</text>
      <input class="input" v-model="form.currency" maxlength="12" />
    </view>
    <view class="field">
      <text>备注</text>
      <textarea class="textarea" v-model="form.note" placeholder="出行说明" />
    </view>

    <button class="primary-button" :loading="saving" :disabled="saving" @tap="saveTrip">保存</button>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { api } from '../../utils/api';
import { today } from '../../utils/format';

const saving = ref(false);
const tripId = ref('');
const form = reactive({
  title: '',
  location: '',
  start_date: today(),
  end_date: '',
  currency: 'CNY',
  note: '',
});

async function loadTrip(id) {
  const payload = await api.getTrip(id);
  Object.assign(form, {
    title: payload.trip.title || '',
    location: payload.trip.location || '',
    start_date: payload.trip.start_date || '',
    end_date: payload.trip.end_date || '',
    currency: payload.trip.currency || 'CNY',
    note: payload.trip.note || '',
  });
}

async function saveTrip() {
  if (!form.title.trim()) {
    uni.showToast({ icon: 'none', title: '请填写出行名称' });
    return;
  }
  saving.value = true;
  try {
    const payload = tripId.value ? await api.updateTrip(tripId.value, form) : await api.createTrip(form);
    const id = payload.trip?.id || tripId.value;
    uni.redirectTo({ url: `/pages/trips/detail?id=${id}` });
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '保存失败' });
  } finally {
    saving.value = false;
  }
}

onLoad((query) => {
  if (query.id) {
    tripId.value = query.id;
    loadTrip(query.id);
  }
});
</script>

<style scoped>
.form-page {
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}
</style>
