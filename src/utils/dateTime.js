const SHANGHAI_TIME_ZONE = 'Asia/Shanghai'
const SHANGHAI_TIME_ZONE_LABEL = 'UTC+08:00'

const dateTimeFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: SHANGHAI_TIME_ZONE,
  calendar: 'gregory',
  numberingSystem: 'latn',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23'
})

function partsFor(date) {
  return dateTimeFormatter.formatToParts(date).reduce((parts, part) => {
    if (part.type !== 'literal') parts[part.type] = part.value
    return parts
  }, {})
}

function validDate(date) {
  return date instanceof Date && !Number.isNaN(date.getTime()) ? date : null
}

/**
 * API timestamps historically omitted an offset while representing UTC.
 * Keep accepting those values during the transition, but never let the
 * browser's local timezone decide how they are displayed.
 */
export function parseDateTime(value) {
  if (value === null || value === undefined || value === '') return null
  if (value instanceof Date) return validDate(value)
  if (typeof value === 'number') return validDate(new Date(value))

  const text = String(value).trim()
  if (!text) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return validDate(new Date(`${text}T00:00:00+08:00`))
  }

  const normalized = text.includes(' ') ? text.replace(' ', 'T') : text
  const hasOffset = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized)
  return validDate(new Date(hasOffset ? normalized : `${normalized}Z`))
}

export function formatDateTime(value) {
  const date = parseDateTime(value)
  if (!date) return '—'
  const parts = partsFor(date)
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second} ${SHANGHAI_TIME_ZONE_LABEL}`
}

export function formatDate(value) {
  if (value === null || value === undefined || value === '') return '—'
  const text = String(value).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text
  const date = parseDateTime(value)
  if (!date) return '—'
  const parts = partsFor(date)
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function formatTime(value) {
  const date = parseDateTime(value)
  if (!date) return '—'
  const parts = partsFor(date)
  return `${parts.hour}:${parts.minute}:${parts.second} ${SHANGHAI_TIME_ZONE_LABEL}`
}

export function shanghaiDateKey(value = new Date()) {
  return formatDate(value)
}

export function shanghaiYear(value = new Date()) {
  const dateKey = shanghaiDateKey(value)
  return /^\d{4}-\d{2}-\d{2}$/.test(dateKey) ? Number(dateKey.slice(0, 4)) : null
}

export function addDaysToDateKey(dateKey, days) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey || '') || !Number.isFinite(days)) return null
  // Treat a date key as a UTC calendar proxy so arithmetic never crosses a
  // browser timezone boundary before the key is formatted.
  const date = new Date(`${dateKey}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + Number(days))
  return date.toISOString().slice(0, 10)
}

export {
  SHANGHAI_TIME_ZONE,
  SHANGHAI_TIME_ZONE_LABEL
}
