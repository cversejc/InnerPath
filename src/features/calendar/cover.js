import { parseDateKey } from './helpers.js'
import { shanghaiDateKey } from '../../utils/dateTime.js'

const VALID_COVER_SEASONS = new Set(['spring', 'summer', 'autumn', 'winter'])
const CHINESE_MONTHS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']

function calendarStartDate(calendar) {
  const firstEntry = calendar?.entries?.find(entry => entry.entry_date || entry.date)
  const dateValue = calendar?.start_date
    || calendar?.startDate
    || firstEntry?.entry_date
    || firstEntry?.date

  if (!dateValue) return null
  const dateText = String(dateValue).slice(0, 10)
  return /^\d{4}-\d{2}-\d{2}$/.test(dateText) ? parseDateKey(dateText) : null
}

function coverDate(calendar, fallbackDate) {
  const startDate = calendarStartDate(calendar)
  if (startDate) return startDate
  const fallbackKey = shanghaiDateKey(fallbackDate)
  return /^\d{4}-\d{2}-\d{2}$/.test(fallbackKey)
    ? parseDateKey(fallbackKey)
    : parseDateKey(shanghaiDateKey())
}

export function selectPublishedCalendar(response) {
  const items = Array.isArray(response?.items) ? response.items : []
  return items.find(item => item.status === 'published' && item.entries?.length) || null
}

export function getCalendarCoverSeason(calendar, fallbackDate = new Date()) {
  const metaPayload = calendar?.meta_payload || calendar?.metaPayload || {}
  const configuredSeason = String(metaPayload.cover_season || metaPayload.coverSeason || '').toLowerCase()
  if (VALID_COVER_SEASONS.has(configuredSeason)) return configuredSeason

  const startDate = coverDate(calendar, fallbackDate)
  const monthDay = (startDate.getUTCMonth() + 1) * 100 + startDate.getUTCDate()

  // Approximate the four seasonal solar-term windows. Calendar metadata can
  // override the theme on a boundary date when its exact solar term is known.
  if (monthDay >= 204 && monthDay < 505) return 'spring'
  if (monthDay >= 505 && monthDay < 807) return 'summer'
  if (monthDay >= 807 && monthDay < 1107) return 'autumn'
  return 'winter'
}

export function buildCalendarCover(calendar, fallbackDate = new Date()) {
  const metaPayload = calendar?.meta_payload || calendar?.metaPayload || {}
  const startDate = coverDate(calendar, fallbackDate)
  const monthName = CHINESE_MONTHS[startDate.getUTCMonth()]
  const coverQuote = typeof metaPayload.cover_quote === 'string'
    ? metaPayload.cover_quote.trim()
    : typeof metaPayload.coverQuote === 'string'
      ? metaPayload.coverQuote.trim()
      : ''
  return {
    title: `辰鉴·${monthName}月决策日历`,
    quote: coverQuote || `${monthName}月宜顺势而为，在节奏里找到自己的定数。`,
    season: getCalendarCoverSeason(calendar, fallbackDate)
  }
}
