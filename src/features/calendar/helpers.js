export const weekdays = ['日', '一', '二', '三', '四', '五', '六']

export function parseDateKey(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatDateKey(date) {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function isToday(dateKey) {
  return formatDateKey(new Date()) === dateKey
}

export function dateKeyFromLabel(label, year) {
  const [, month, day] = label.match(/(\d+)月(\d+)日/) || []
  if (!month || !day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}
