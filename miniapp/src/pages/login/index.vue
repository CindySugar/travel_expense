<template>
  <view class="page login-page">
    <view class="hero">
      <text class="eyebrow">Trip Ledger</text>
      <text class="title">朋友出游记账</text>
      <text class="muted">用微信登录后创建出行、记录账单，并自动算清每个人应收应补。</text>
    </view>

    <view class="card login-card">
      <button class="primary-button" :loading="loading" :disabled="loading" @tap="loginWithWechat">
        微信一键登录
      </button>
      <button v-if="isDev" class="secondary-button" :loading="loading" :disabled="loading" @tap="loginWithMockCode">
        开发环境模拟登录
      </button>
      <view class="api-line">
        <text class="muted">API</text>
        <input class="input api-input" v-model="apiBaseUrl" confirm-type="done" @blur="saveApiBaseUrl" />
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { api, getApiBaseUrl, setToken } from '../../utils/api';

const loading = ref(false);
const apiBaseUrl = ref(getApiBaseUrl());
const isDev = true;

function saveApiBaseUrl() {
  uni.setStorageSync('apiBaseUrl', apiBaseUrl.value.trim() || 'http://127.0.0.1:8000');
}

function finishLogin(payload) {
  setToken(payload.token);
  uni.reLaunch({ url: '/pages/trips/index' });
}

async function submitCode(code) {
  loading.value = true;
  saveApiBaseUrl();
  try {
    const payload = await api.wechatLogin(code);
    finishLogin(payload);
  } catch (error) {
    uni.showToast({ icon: 'none', title: error.message || '登录失败' });
  } finally {
    loading.value = false;
  }
}

function loginWithWechat() {
  uni.login({
    provider: 'weixin',
    success(result) {
      if (!result.code) {
        uni.showToast({ icon: 'none', title: '未获取到微信登录凭证' });
        return;
      }
      submitCode(result.code);
    },
    fail() {
      uni.showToast({ icon: 'none', title: '微信登录失败' });
    },
  });
}

function loginWithMockCode() {
  submitCode(`mock:${Date.now()}`);
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 56rpx;
}

.hero {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
  padding-top: 72rpx;
}

.login-card {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.api-line {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.api-input {
  flex: 1;
  min-width: 0;
  font-size: 24rpx;
}
</style>
