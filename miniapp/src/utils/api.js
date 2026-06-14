const TOKEN_KEY = 'miniappToken';

export function getApiBaseUrl() {
  return uni.getStorageSync('apiBaseUrl') || 'http://127.0.0.1:8000';
}

export function getToken() {
  return uni.getStorageSync(TOKEN_KEY) || '';
}

export function setToken(token) {
  uni.setStorageSync(TOKEN_KEY, token || '');
}

export function clearToken() {
  uni.removeStorageSync(TOKEN_KEY);
}

function redirectToLogin() {
  clearToken();
  uni.reLaunch({ url: '/pages/login/index' });
}

export function request(path, options = {}) {
  const token = getToken();
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${getApiBaseUrl()}${path}`,
      method: options.method || 'GET',
      data: options.data,
      header: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.header || {}),
      },
      success(response) {
        const payload = response.data || {};
        if (response.statusCode === 401) {
          redirectToLogin();
          reject(new Error(payload.error || '登录已失效'));
          return;
        }
        if (response.statusCode < 200 || response.statusCode >= 300 || payload.ok === false) {
          reject(new Error(payload.error || `请求失败：${response.statusCode}`));
          return;
        }
        resolve(payload);
      },
      fail(error) {
        reject(new Error(error.errMsg || '网络连接失败'));
      },
    });
  });
}

export const api = {
  wechatLogin: (code) => request('/api/auth/wechat-login/', { method: 'POST', data: { code } }),
  listTrips: () => request('/api/trips/'),
  createTrip: (data) => request('/api/trips/', { method: 'POST', data }),
  updateTrip: (tripId, data) => request(`/api/trips/${tripId}/`, { method: 'PATCH', data }),
  deleteTrip: (tripId) => request(`/api/trips/${tripId}/`, { method: 'DELETE' }),
  getTrip: (tripId) => request(`/api/trips/${tripId}/`),
  listMembers: (tripId) => request(`/api/trips/${tripId}/members/`),
  addMember: (tripId, data) => request(`/api/trips/${tripId}/members/`, { method: 'POST', data }),
  deleteMember: (memberId) => request(`/api/members/${memberId}/`, { method: 'DELETE' }),
  listExpenses: (tripId) => request(`/api/trips/${tripId}/expenses/`),
  addExpense: (tripId, data) => request(`/api/trips/${tripId}/expenses/`, { method: 'POST', data }),
  deleteExpense: (expenseId) => request(`/api/expenses/${expenseId}/`, { method: 'DELETE' }),
  getSummary: (tripId) => request(`/api/trips/${tripId}/summary/`),
  listSettlements: (tripId) => request(`/api/trips/${tripId}/settlements/`),
  updateSettlement: (settlementId, data) =>
    request(`/api/settlements/${settlementId}/`, { method: 'PATCH', data }),
};
