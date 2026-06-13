async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return null;
  }
  return response.json();
}

function toApiError(payload, fallbackStatus) {
  if (payload?.error) return payload.error;
  if (payload?.detail) return payload.detail;
  return `请求失败（${fallbackStatus}）`;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await parseResponse(response);

  if (!response.ok || payload?.ok === false) {
    throw new Error(toApiError(payload, response.status));
  }

  return payload || { ok: true };
}

export const api = {
  me: () => request('/api/auth/me/'),
  register: (data) => request('/api/auth/register/', { method: 'POST', body: data }),
  login: (data) => request('/api/auth/login/', { method: 'POST', body: data }),
  logout: () => request('/api/auth/logout/', { method: 'POST' }),
  listTrips: () => request('/api/trips/'),
  createTrip: (data) => request('/api/trips/', { method: 'POST', body: data }),
  updateTrip: (tripId, data) => request(`/api/trips/${tripId}/`, { method: 'PATCH', body: data }),
  deleteTrip: (tripId) => request(`/api/trips/${tripId}/`, { method: 'DELETE' }),
  getTrip: (tripId) => request(`/api/trips/${tripId}/`),
  listMembers: (tripId) => request(`/api/trips/${tripId}/members/`),
  addMember: (tripId, data) => request(`/api/trips/${tripId}/members/`, { method: 'POST', body: data }),
  deleteMember: (memberId) => request(`/api/members/${memberId}/`, { method: 'DELETE' }),
  listExpenses: (tripId) => request(`/api/trips/${tripId}/expenses/`),
  addExpense: (tripId, data) => request(`/api/trips/${tripId}/expenses/`, { method: 'POST', body: data }),
  updateExpense: (expenseId, data) => request(`/api/expenses/${expenseId}/`, { method: 'PATCH', body: data }),
  deleteExpense: (expenseId) => request(`/api/expenses/${expenseId}/`, { method: 'DELETE' }),
  getSummary: (tripId) => request(`/api/trips/${tripId}/summary/`),
  listSettlements: (tripId) => request(`/api/trips/${tripId}/settlements/`),
  updateSettlement: (settlementId, data) =>
    request(`/api/settlements/${settlementId}/`, { method: 'PATCH', body: data }),
};
