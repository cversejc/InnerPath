<script setup>
import { computed, ref, watch } from 'vue'
import CalendarPlanningSection from '../../calendar/components/CalendarPlanningSection.vue'
import { isToday, parseDateKey, weekdays } from '../../calendar/helpers.js'
import '../../../views/Calendar.css'

const props = defineProps({
  calendar: { type: Object, required: true },
  decisionLogs: { type: Array, default: () => [] }
})

const selectedDate = ref('')
const showFullGuidance = ref(false)

const days = computed(() => (props.calendar.entries || []).map(entry => {
  const entryDate = String(entry.entry_date || entry.date || '').slice(0, 10)
  if (!entryDate) return null
  const date = parseDateKey(entryDate)
  return {
    ...entry,
    date: entryDate,
    month: date.getUTCMonth() + 1,
    day: date.getUTCDate(),
    weekday: weekdays[date.getUTCDay()],
    dayPillar: entry.day_pillar || entry.dayPillar || '',
    statusLabel: entry.status_label || entry.statusLabel || '',
    shortLabel: entry.keyword || entry.shortLabel || entry.status_label || entry.statusLabel || '查看',
    phaseId: entry.phase_id || entry.phaseId || entry.tone || 'default',
    phaseLabel: entry.phase_label || entry.phaseLabel || entry.status_label || entry.statusLabel || entry.tone || '',
    timeWindow: entry.time_window || entry.timeWindow || '按你的节奏安排，给决定留出换气空间。',
    suitable: entry.suitable || [],
    unsuitable: entry.unsuitable || [],
    tone: entry.tone || 'yellow',
    isPhase: entry.is_phase ?? entry.isPhase ?? false
  }
}).filter(Boolean))

const calendarMeta = computed(() => props.calendar.meta_payload || props.calendar.metaPayload || {})
const todayDate = computed(() => days.value.find(day => isToday(day.date))?.date || days.value[0]?.date || '')
const selectedDay = computed(() => days.value.find(day => day.date === selectedDate.value) || days.value[0] || {})
const selectedEntry = computed(() => selectedDay.value)
const selectedRecords = computed(() => props.decisionLogs
  .filter(log => (log.log_date || log.date) === selectedDate.value)
  .map(log => ({
    ...log,
    date: log.log_date || log.date,
    createdAt: log.created_at || log.createdAt
  })))

const calendarLabel = computed(() => {
  const start = props.calendar.start_date || days.value[0]?.date
  const end = props.calendar.end_date || days.value[days.value.length - 1]?.date
  if (!start || !end) return '个人日历'
  return `${start.slice(0, 7).replace('-', ' / ')}—${end.slice(0, 7).replace('-', ' / ')}`
})

const meta = computed(() => ({
  ...calendarMeta.value,
  title: props.calendar.title,
  subtitle: calendarMeta.value.subtitle || 'PERSONAL TIMEZONE',
  dateLabel: calendarMeta.value.dateLabel || `${props.calendar.start_date || days.value[0]?.date || ''} — ${props.calendar.end_date || days.value[days.value.length - 1]?.date || ''}`,
  rhythm: calendarMeta.value.rhythm || '少说，多做，多记录',
  intro: calendarMeta.value.intro || '这是一张属于你的决策时机参照系，帮你在重要选择前留出观察、行动与复盘的空间。'
}))

const recordCountByDate = computed(() => props.decisionLogs.reduce((counts, log) => {
  const date = log.log_date || log.date
  if (date) counts[date] = (counts[date] || 0) + 1
  return counts
}, {}))

const calendarCells = computed(() => {
  if (!days.value.length) return []
  const firstDate = parseDateKey(days.value[0].date)
  const leading = (firstDate.getDay() + 6) % 7
  const trailing = (7 - ((leading + days.value.length) % 7)) % 7
  const emptyCells = Array.from({ length: leading + trailing }, (_, index) => ({ key: `empty-${index}`, empty: true }))
  return [
    ...emptyCells.slice(0, leading),
    ...days.value.map(day => ({
      ...day,
      key: day.date,
      isCurrentDay: isToday(day.date),
      recordCount: recordCountByDate.value[day.date] || 0
    })),
    ...emptyCells.slice(leading)
  ]
})

const phases = computed(() => {
  const grouped = []
  for (const day of days.value) {
    const existing = grouped.find(phase => phase.id === day.phaseId)
    if (existing) {
      existing.endDate = day.date
      existing.dateRange = `${existing.startDate}—${existing.endDate}`
    } else {
      grouped.push({
        id: day.phaseId,
        label: day.phaseLabel || day.shortLabel,
        tone: day.tone,
        startDate: day.date,
        endDate: day.date,
        dateRange: day.date
      })
    }
  }
  return grouped
})

const monthRecordCount = computed(() => props.decisionLogs.filter(log => days.value.some(
  day => day.date === (log.log_date || log.date)
)).length)
const monthRecordDays = computed(() => new Set(props.decisionLogs.filter(log => days.value.some(
  day => day.date === (log.log_date || log.date)
)).map(log => log.log_date || log.date)).size)

const actionClimate = computed(() => ({
  green: { label: '推进窗口', caption: '适合把已经想清楚的事做成。', position: 84 },
  'green-yellow': { label: '先推进，再收束', caption: '上午打开行动，后半天留一点余地。', position: 72 },
  'yellow-green': { label: '先准备，再行动', caption: '先把信息理顺，下午再迈出下一步。', position: 58 },
  yellow: { label: '观察与准备', caption: '今天更适合整理判断，而不是急着拍板。', position: 45 },
  'red-yellow': { label: '缓冲后再判断', caption: '先降低消耗，等思路重新变得清楚。', position: 29 },
  red: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 },
  rest: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 }
}[selectedEntry.value.tone] || {
  label: '观察与准备', caption: '今天更适合整理判断，而不是急着拍板。', position: 45
}))

const visibleSuitable = computed(() => {
  const suitable = selectedEntry.value.suitable || []
  return showFullGuidance.value ? suitable : suitable.slice(0, 2)
})
const visibleUnsuitable = computed(() => {
  const unsuitable = selectedEntry.value.unsuitable || []
  return showFullGuidance.value ? unsuitable : unsuitable.slice(0, 1)
})
const hiddenGuidanceCount = computed(() => showFullGuidance.value ? 0 :
  Math.max(0, (selectedEntry.value.suitable || []).length - 2) +
  Math.max(0, (selectedEntry.value.unsuitable || []).length - 1))
const rhythmSegments = computed(() => {
  const rhythmByTone = {
    green: [['上午', '聚焦', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
    'green-yellow': [['上午', '表达', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
    'yellow-green': [['上午', '观察', 'yellow'], ['下午', '启动', 'green'], ['晚上', '整理', 'yellow']],
    yellow: [['上午', '观察', 'yellow'], ['下午', '准备', 'yellow'], ['晚上', '轻推', 'green']],
    'red-yellow': [['上午', '缓冲', 'red'], ['下午', '整理', 'yellow'], ['晚上', '收气', 'red']],
    red: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']],
    rest: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']]
  }
  return (rhythmByTone[selectedEntry.value.tone] || rhythmByTone.yellow)
    .map(([period, label, tone]) => ({ period, label, tone }))
})

watch(() => props.calendar.id, () => {
  selectedDate.value = todayDate.value
  showFullGuidance.value = false
}, { immediate: true })

function selectDate(date) {
  selectedDate.value = date
}
</script>

<template>
  <div class="calendar-page calendar-admin-preview">
    <div class="calendar-preview-banner">
      <span class="calendar-preview-mark" aria-hidden="true">辰</span>
      <div><strong>用户端日历视图</strong><span>管理员只读 · {{ calendar.status === 'published' ? '已发布' : calendar.status || '日历' }}</span></div>
    </div>
    <CalendarPlanningSection
      v-if="days.length"
      :action-climate="actionClimate"
      :calendar-cells="calendarCells"
      :calendar-label="calendarLabel"
      :hidden-guidance-count="hiddenGuidanceCount"
      :is-mobile-layout="false"
      :meta="meta"
      :month-record-count="monthRecordCount"
      :month-record-days="monthRecordDays"
      :mobile-detail-open="true"
      :phases="phases"
      :read-only="true"
      :record-draft="{ kind: 'action', status: 'done', content: '', note: '' }"
      record-source="api"
      :record-error="''"
      :record-feedback="''"
      :rhythm-segments="rhythmSegments"
      :saving-record="false"
      :selected-date="selectedDate"
      :selected-day="selectedDay"
      :selected-entry="selectedEntry"
      :selected-records="selectedRecords"
      :show-full-guidance="showFullGuidance"
      :show-record-form="false"
      :today-date="todayDate"
      :visible-suitable="visibleSuitable"
      :visible-unsuitable="visibleUnsuitable"
      :weekdays="weekdays.slice(1).concat(weekdays[0])"
      @select-date="selectDate"
      @show-current-date="selectDate(todayDate)"
      @toggle-guidance="showFullGuidance = !showFullGuidance"
    />
    <p v-else class="calendar-preview-empty">此版本没有可展示的每日条目。</p>
  </div>
</template>

<style scoped>
.calendar-preview-banner { display: flex; align-items: center; gap: 12px; margin: 0 0 18px; border-bottom: 1px solid var(--line); padding: 0 0 14px; }
.calendar-preview-mark { display: grid; flex: 0 0 36px; place-items: center; width: 36px; aspect-ratio: 1; border: 1px solid var(--cinnabar); color: var(--cinnabar-deep); font: var(--weight-semibold) 16px/1 var(--font-display); }
.calendar-preview-banner div { display: grid; gap: 3px; }
.calendar-preview-banner strong { color: var(--ink); font-size: 14px; }
.calendar-preview-banner span:not(.calendar-preview-mark) { color: var(--muted); font-size: 11px; }
.calendar-preview-empty { padding: 30px 12px; color: var(--muted); text-align: center; }
.calendar-admin-preview :deep(.calendar-section) { padding: 0; background: transparent; }
.calendar-admin-preview :deep(.calendar-section > .container) { width: 100%; max-width: none; }
.calendar-admin-preview :deep(.calendar-section-heading) { align-items: start; margin-bottom: 16px; }
.calendar-admin-preview :deep(.calendar-layout) { grid-template-columns: minmax(0, 1fr); gap: 12px; }
.calendar-admin-preview :deep(.day-detail) { position: relative; top: auto; z-index: auto; max-height: none; overflow: visible; opacity: 1; visibility: visible; transform: none; }
.calendar-admin-preview :deep(.detail-close),
.calendar-admin-preview :deep(.mobile-detail-launch) { display: none !important; }
.calendar-admin-preview :deep(.calendar-grid-scroll) { overflow-x: auto; }
.calendar-admin-preview :deep(.calendar-weekdays),
.calendar-admin-preview :deep(.calendar-grid) { min-width: 440px; }
.calendar-admin-preview :deep(.date-cell),
.calendar-admin-preview :deep(.calendar-empty) { min-height: 86px; }
@media (max-width: 640px) {
  .calendar-admin-preview :deep(.calendar-weekdays),
  .calendar-admin-preview :deep(.calendar-grid) { min-width: 336px; }
  .calendar-admin-preview :deep(.date-cell),
  .calendar-admin-preview :deep(.calendar-empty) { min-height: 64px; }
}
</style>
