export function formatMoney(value) {
  const amount = Number(value || 0);
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  return `¥${safeAmount.toFixed(2)}`;
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function dateRange(trip) {
  if (!trip) return '未设置日期';
  if (trip.start_date && trip.end_date) return `${trip.start_date} 至 ${trip.end_date}`;
  return trip.start_date || trip.end_date || '未设置日期';
}

export function statusText(status) {
  const labels = {
    planned: '未出发',
    ongoing: '进行中',
    completed: '已结束',
    draft: '草稿',
  };
  return labels[status] || '草稿';
}
