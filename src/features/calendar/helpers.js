import { shanghaiDateKey } from '../../utils/dateTime.js'

export const weekdays = ['日', '一', '二', '三', '四', '五', '六']

export function parseDateKey(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day))
}

export function formatDateKey(date) {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`
}

export function isToday(dateKey) {
  return shanghaiDateKey() === dateKey
}

export function dateKeyFromLabel(label, year) {
  const [, month, day] = label.match(/(\d+)月(\d+)日/) || []
  if (!month || !day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}
