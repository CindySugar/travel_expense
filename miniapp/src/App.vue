<template>
  <slot />
</template>

<script>
export default {
  onLaunch() {
    const apiBaseUrl = uni.getStorageSync('apiBaseUrl');
    if (!apiBaseUrl) {
      uni.setStorageSync('apiBaseUrl', 'http://127.0.0.1:8000');
    }
  },
};
</script>

<style>
page {
  min-height: 100%;
  background: #f6f7f2;
  color: #17201b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button {
  margin: 0;
}

.page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32rpx;
}

.eyebrow {
  color: #6a756f;
  font-size: 24rpx;
  font-weight: 600;
  letter-spacing: 0;
}

.title {
  color: #17201b;
  font-size: 44rpx;
  font-weight: 800;
  line-height: 1.15;
}

.muted {
  color: #69746f;
}

.card {
  background: #ffffff;
  border: 1rpx solid #e0e5df;
  border-radius: 12rpx;
  box-sizing: border-box;
  padding: 28rpx;
}

.primary-button,
.secondary-button,
.danger-button {
  border-radius: 10rpx;
  font-size: 30rpx;
  font-weight: 700;
  line-height: 88rpx;
}

.primary-button {
  background: #1f7a4d;
  color: #ffffff;
}

.secondary-button {
  background: #edf4ee;
  color: #1f6e49;
}

.danger-button {
  background: #fff0ee;
  color: #a9362b;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  color: #3d4943;
  font-size: 26rpx;
  font-weight: 700;
}

.input,
.textarea,
.picker-value {
  min-height: 84rpx;
  border: 1rpx solid #dfe5de;
  border-radius: 10rpx;
  box-sizing: border-box;
  padding: 0 22rpx;
  background: #fbfcfa;
  color: #17201b;
  font-size: 30rpx;
  font-weight: 500;
}

.textarea {
  min-height: 150rpx;
  padding-top: 20rpx;
}

.picker-value {
  display: flex;
  align-items: center;
}

.empty {
  padding: 48rpx 24rpx;
  color: #6d7772;
  text-align: center;
}
</style>
