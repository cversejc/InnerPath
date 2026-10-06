<script setup>
import { ref } from 'vue'
import { Button as VanButton } from 'vant'
import CalendarDayDetail from './CalendarDayDetail.vue'

const props = defineProps({
  actionClimate: { type: Object, required: true },
  calendarCells: { type: Array, default: () => [] },
  calendarLabel: { type: String, default: '' },
  hiddenGuidanceCount: { type: Number, default: 0 },
  isMobileLayout: { type: Boolean, default: false },
  meta: { type: Object, default: () => ({}) },
  monthRecordCount: { type: Number, default: 0 },
  monthRecordDays: { type: Number, default: 0 },
  mobileDetailOpen: { type: Boolean, default: false },
  phases: { type: Array, default: () => [] },
  recordDraft: { type: Object, required: true },
  recordError: { type: String, default: '' },
  recordFeedback: { type: String, default: '' },
  recordSource: { type: String, default: 'local' },
  readOnly: { type: Boolean, default: false },
  rhythmSegments: { type: Array, default: () => [] },
  savingRecord: { type: Boolean, default: false },
  selectedDate: { type: String, default: '' },
  selectedDay: { type: Object, default: () => ({}) },
  selectedEntry: { type: Object, default: () => ({}) },
  selectedRecords: { type: Array, default: () => [] },
  showFullGuidance: { type: Boolean, default: false },
  showRecordForm: { type: Boolean, default: false },
  todayDate: { type: String, default: '' },
  visibleSuitable: { type: Array, default: () => [] },
  visibleUnsuitable: { type: Array, default: () => [] },
  weekdays: { type: Array, default: () => [] }
})

const emit = defineEmits([
  'close-mobile-detail',
  'detail-keydown',
  'close-record-form',
  'open-mobile-detail',
  'open-record-form',
  'quick-record',
  'remove-record',
  'save-record',
  'select-date',
  'show-current-date',
  'toggle-guidance',
  'update-record-draft'
])

const detailTrigger = ref(null)
const dayDetail = ref(null)

function focusCloseButton() {
  dayDetail.value?.focusCloseButton()
}

function focusTrigger() {
  const trigger = detailTrigger.value?.$el || detailTrigger.value
  trigger?.focus()
}

function focusContainer() {
  dayDetail.value?.focusContainer()
}

function getFocusableItems() {
  return dayDetail.value?.getFocusableItems() || []
}

defineExpose({ focusCloseButton, focusContainer, focusTrigger, getFocusableItems })
</script>

<template>
  <section class="section-band calendar-section">
    <div class="container">
      <div class="calendar-section-heading">
        <div>
          <p class="section-kicker">DAILY NAVIGATION</p>
          <h2 class="section-title">看见时机，也留下发生过的事</h2>
        </div>
        <div class="calendar-heading-side">
          <div class="calendar-trace-summary" aria-live="polite">
            <span>本月行动轨迹</span>
            <strong>{{ monthRecordDays }}天 · {{ monthRecordCount }}条</strong>
          </div>
          <div class="legend" aria-label="时区颜色图例">
            <span><i class="legend-dot legend-dot-green"></i>推进</span>
            <span><i class="legend-dot legend-dot-yellow"></i>准备</span>
            <span><i class="legend-dot legend-dot-red"></i>休整</span>
            <span><i class="legend-dot legend-dot-record"></i>已记录</span>
          </div>
        </div>
      </div>

      <div class="calendar-layout">
        <section class="paper-card month-board" :aria-label="`${calendarLabel}日历`">
          <header class="month-board-head">
            <div>
              <span class="month-eyebrow">PERSONAL TIMEZONE</span>
              <h3>{{ calendarLabel }}</h3>
              <p>{{ meta.dateLabel }}</p>
            </div>
            <VanButton class="today-button" type="default" plain round native-type="button" @click="$emit('show-current-date')">
              回到当前聚焦 <IconMark name="arrow" />
            </VanButton>
          </header>

          <div
            class="calendar-grid-scroll"
            :tabindex="isMobileLayout ? 0 : -1"
            :aria-label="isMobileLayout ? '日期网格，可横向滑动查看完整一周' : undefined"
          >
            <div class="calendar-weekdays" aria-hidden="true">
              <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
            </div>

            <div class="calendar-grid" role="group" aria-label="本月日期">
              <template v-for="cell in calendarCells" :key="cell.key">
                <div v-if="cell.empty" class="calendar-empty" aria-hidden="true"></div>
                <button
                  v-else
                  type="button"
                  class="date-cell"
                  :class="[`tone-${cell.tone}`, { selected: selectedDate === cell.date, 'is-today': cell.isCurrentDay }]"
                  :aria-label="`${cell.month}月${cell.day}日，${cell.statusLabel}${cell.recordCount ? `，已有${cell.recordCount}条记录` : ''}`"
                  :aria-pressed="selectedDate === cell.date"
                  @click="$emit('select-date', cell.date)"
                >
                  <span class="date-cell-top"><strong>{{ String(cell.day).padStart(2, '0') }}</strong><em v-if="cell.month === 10">十月</em></span>
                  <span class="date-cell-pillar">{{ cell.dayPillar || cell.shortLabel }}</span>
                  <span class="date-cell-keyword">{{ cell.keyword || cell.shortLabel }}</span>
                  <span class="date-cell-status">{{ cell.statusLabel }}</span>
                  <span v-if="cell.recordCount" class="date-cell-record"><i></i>{{ cell.recordCount }}条记录</span>
                  <span v-if="cell.isCurrentDay" class="today-mark">今天</span>
                </button>
              </template>
            </div>
          </div>

          <VanButton v-if="!mobileDetailOpen" ref="detailTrigger" class="mobile-detail-launch" type="default" plain round native-type="button" @click="$emit('open-mobile-detail')">
            查看 {{ selectedDay.month }}月{{ selectedDay.day }}日的建议与记录 <IconMark name="arrow" />
          </VanButton>
        </section>

        <CalendarDayDetail
          ref="dayDetail"
          :action-climate="actionClimate"
          :hidden-guidance-count="hiddenGuidanceCount"
          :is-mobile-layout="isMobileLayout"
          :mobile-detail-open="mobileDetailOpen"
          :record-draft="recordDraft"
          :record-error="recordError"
          :record-feedback="recordFeedback"
          :record-source="recordSource"
          :read-only="readOnly"
          :rhythm-segments="rhythmSegments"
          :saving-record="savingRecord"
          :selected-date="selectedDate"
          :selected-day="selectedDay"
          :selected-entry="selectedEntry"
          :selected-records="selectedRecords"
          :show-full-guidance="showFullGuidance"
          :show-record-form="showRecordForm"
          :today-date="todayDate"
          :visible-suitable="visibleSuitable"
          :visible-unsuitable="visibleUnsuitable"
          @close-mobile-detail="emit('close-mobile-detail')"
          @detail-keydown="emit('detail-keydown', $event)"
          @close-record-form="emit('close-record-form')"
          @open-record-form="emit('open-record-form')"
          @quick-record="emit('quick-record', $event)"
          @remove-record="emit('remove-record', $event)"
          @save-record="emit('save-record')"
          @show-current-date="emit('show-current-date')"
          @toggle-guidance="emit('toggle-guidance')"
          @update-record-draft="emit('update-record-draft', $event)"
        />
      </div>

      <div class="phase-rail" aria-label="月度能量阶段">
        <button
          v-for="(phase, index) in phases"
          :key="phase.id"
          type="button"
          class="phase-card"
          :class="[`tone-${phase.tone}`, { active: selectedEntry.phaseId === phase.id }]"
          :aria-pressed="selectedEntry.phaseId === phase.id"
          @click="$emit('select-date', phase.startDate)"
        >
          <span class="phase-card-index">0{{ index + 1 }}</span>
          <span class="phase-card-copy"><strong>{{ phase.label }}</strong><small>{{ phase.dateRange }}</small></span>
          <IconMark name="arrow" class="phase-card-arrow" />
        </button>
      </div>
    </div>
  </section>
</template>
