<template>
  <view class="page form-page">
    <view class="field">
      <text>金额</text>
      <input class="input" v-model="form.amount" type="digit" placeholder="90.00" />
    </view>
    <view class="field">
      <text>付款人</text>
      <picker :range="memberNames" :value="payerIndex" @change="setPayer">
        <view class="picker-value">{{ payerName || '选择付款人' }}</view>
      </picker>
    </view>
    <view class="field">
      <text>日期</text>
      <picker mode="date" :value="form.spent_at" @change="form.spent_at = $event.detail.value">
        <view class="picker-value">{{ form.spent_at }}</view>
      </picker>
    </view>
    <view class="field">
      <text>分类</text>
      <input class="input" v-model="form.category" placeholder="餐饮" />
    </view>
    <view class="field">
      <text>说明</text>
      <input class="input" v-model="form.description" placeholder="午餐、门票、打车" />
    </view>

    <view class="card split-card">
      <view class="section-head">
        <text class="section-title">参与分摊</text>
        <button class="secondary-button small-button" @tap="selectAll">全选</button>
      </view>
      <checkbox-group @change="setSplitMembers">
        <label v-for="member in members" :key="member.id" class="check-row">
          <checkbox :value="String(member.id)" :checked="form.split_member_ids.includes(member.id)" />
          <text>{{ member.display_name }}</text>
        </label>
      </checkbox-group>
    </view>

    <button class="primary-button" :loading="saving" :disabled="saving" @tap="saveExpense">保存账单</button>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { api } from '../../utils/api';
import { today } from '../../utils/format';

const tripId = ref('');
const saving = ref(false);
const members = ref([]);
const form = reactive({
  amount: '',
  payer_id: '',
  category: '餐饮',
  spent_at: today(),
  description: '',
  split_member_ids: [],
});

const memberNames = computed(() => members.value.map((member) => member.display_name));
const payerIndex = computed(() => members.value.findIndex((member) => member.id === Number(form.payer_id)));
const payerName = computed(() => members.value.find((member) => member.id === Number(form.payer_id))?.display_name || '');

async function loadMembers() {
  const payload = await api.listMembers(tripId.value);
  members.value = payload.members || [];
  form.payer_id = members.value[0]?.id || '';
  form.split_member_ids = members.value.map((member) => member.id);
}

function setPayer(event) {
  const member = members.value[Number(event.detail.value)];
  form.payer_id = member?.id || '';
}

function setSplitMembers(event) {
  form.split_member_ids = event.detail.value.map((value) => Number(value));
}

function selectAll() {
  form.split_member_ids = members.value.map((member) => member.id);
}

async function saveExpense() {
  if (!form.amount || Number(form.amount) <= 0) {
    uni.showToast({ icon: 'none', title: '请填写正确金额' });
    return;
  }
  if (!form.payer_id) {
    uni.showToast({ icon: 'none', title: '请选择付款人' });
    return;
  }
  if (!form.split_member_ids.length) {
    uni.showToast({ icon: 'none', title: '请选择分摊成员' });
    return;
  }

  saving.value = true;
  try {
    await api.addExpense(tripId.value, {
      ...form,
      payer_id: Number(form.payer_id),
      split_member_ids: form.split_member_ids,
    });
    uni.navigateBack();
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '保存失败' });
  } finally {
    saving.value = false;
  }
}

onLoad((query) => {
  tripId.value = query.tripId || '';
  if (tripId.value) loadMembers();
});
</script>

<style scoped>
.form-page,
.split-card,
checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 26rpx;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  color: #17201b;
  font-size: 32rpx;
  font-weight: 800;
}

.small-button {
  width: 118rpx;
  line-height: 64rpx;
  font-size: 25rpx;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 18rpx;
  color: #24302a;
  font-size: 30rpx;
  min-height: 56rpx;
}
</style>
