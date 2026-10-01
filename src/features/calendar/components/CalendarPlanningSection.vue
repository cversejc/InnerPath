<script setup>
import { ref } from 'vue'
import ActionRecordsSection from './ActionRecordsSection.vue'

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
  dayDetail.value?.querySelector('.detail-close')?.focus()
}

function focusTrigger() {
  detailTrigger.value?.focus()
}

function focusContainer() {
  dayDetail.value?.focus()
}

function getFocusableItems() {
  return Array.from(dayDetail.value?.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
  ) || [])
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
            <button class="today-button" type="button" @click="$emit('show-current-date')">回到当前聚焦 <IconMark name="arrow" /></button>
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

          <button v-if="!mobileDetailOpen" ref="detailTrigger" class="mobile-detail-launch" type="button" @click="$emit('open-mobile-detail')">
            查看 {{ selectedDay.month }}月{{ selectedDay.day }}日的建议与记录 <IconMark name="arrow" />
          </button>
        </section>

        <aside
          ref="dayDetail"
          class="paper-card day-detail"
          :class="{ 'is-open': mobileDetailOpen }"
          :role="isMobileLayout && mobileDetailOpen ? 'dialog' : 'complementary'"
          :aria-modal="isMobileLayout && mobileDetailOpen ? 'true' : undefined"
          aria-labelledby="day-detail-title"
          tabindex="-1"
          @keydown="$emit('detail-keydown', $event)"
        >
          <button class="detail-close" type="button" aria-label="关闭日期详情" @click="$emit('close-mobile-detail')"><IconMark name="close" /></button>
          <div class="detail-header">
            <div>
              <span class="detail-kicker">{{ selectedEntry.isPhase ? 'PHASE NAVIGATION' : 'DAY NAVIGATION' }}</span>
              <h3 id="day-detail-title">{{ selectedDay.month }}月{{ selectedDay.day }}日 <small>星期{{ selectedDay.weekday }}</small></h3>
            </div>
            <span class="status-pill" :class="`tone-${selectedEntry.tone}`">{{ selectedEntry.statusLabel }}</span>
          </div>

          <div class="detail-title-row">
            <span class="detail-pillar">{{ selectedDay.dayPillar || selectedEntry.dateRange }}</span>
            <span class="detail-phase">{{ selectedEntry.phaseLabel }}</span>
          </div>
          <div class="day-signal-card">
            <div class="day-signal-top">
              <div class="day-signal-copy">
                <span class="detail-section-kicker">ACTION CLIMATE</span>
                <strong>{{ actionClimate.label }}</strong>
                <p>{{ actionClimate.caption }}</p>
              </div>
              <div class="keyword-stamp" aria-label="今日关键词">
                <strong>{{ selectedEntry.keyword }}</strong>
                <span>关键词</span>
              </div>
            </div>
            <div class="climate-meter" :aria-label="`行动气候：${actionClimate.label}`">
              <div class="climate-meter-labels"><span>休整</span><span>观察</span><span>推进</span></div>
              <div class="climate-meter-track">
                <span class="climate-meter-fill" :class="`tone-${selectedEntry.tone}`" :style="{ width: `${actionClimate.position}%` }"></span>
                <i :class="`tone-${selectedEntry.tone}`" :style="{ left: `${actionClimate.position}%` }"></i>
              </div>
            </div>
          </div>
          <p class="detail-summary">{{ selectedEntry.summary || `这一日适合把“${selectedEntry.keyword}”放在第一位。` }}</p>

          <div class="rhythm-strip">
            <div class="rhythm-strip-head"><span>今日节奏</span><small>把力气放在合适的时段</small></div>
            <div class="rhythm-track" aria-label="今日节奏分段">
              <div v-for="segment in rhythmSegments" :key="segment.period" class="rhythm-segment" :class="`rhythm-${segment.tone}`">
                <span>{{ segment.period }}</span><strong>{{ segment.label }}</strong>
              </div>
            </div>
            <p class="rhythm-note">{{ selectedEntry.timeWindow }}</p>
          </div>

          <div class="guidance-grid">
            <div class="guidance-card guidance-good">
              <div class="guidance-card-head"><span>适合做</span><b>{{ selectedEntry.suitable.length }}</b></div>
              <ul><li v-if="!selectedEntry.suitable.length" class="guidance-empty">暂无明确建议</li><li v-for="item in visibleSuitable" :key="item">{{ item }}</li></ul>
            </div>
            <div class="guidance-card guidance-bad">
              <div class="guidance-card-head"><span>先不要做</span><b>{{ selectedEntry.unsuitable.length }}</b></div>
              <ul><li v-if="!selectedEntry.unsuitable.length" class="guidance-empty">暂无特别避开事项</li><li v-for="item in visibleUnsuitable" :key="item">{{ item }}</li></ul>
            </div>
          </div>
          <button v-if="hiddenGuidanceCount" class="guidance-toggle" type="button" @click="$emit('toggle-guidance')">
            {{ showFullGuidance ? '收起详细建议' : `展开其余 ${hiddenGuidanceCount} 条建议` }} <span>{{ showFullGuidance ? '↑' : '↓' }}</span>
          </button>

          <ActionRecordsSection
            :record-draft="recordDraft"
            :record-error="recordError"
            :record-feedback="recordFeedback"
            :record-source="recordSource"
            :saving-record="savingRecord"
            :selected-date="selectedDate"
            :selected-entry="selectedEntry"
            :selected-records="selectedRecords"
            :show-record-form="showRecordForm"
            :today-date="todayDate"
            @close-record-form="emit('close-record-form')"
            @open-record-form="emit('open-record-form')"
            @quick-record="emit('quick-record', $event)"
            @remove-record="emit('remove-record', $event)"
            @save-record="emit('save-record')"
            @update-record-draft="emit('update-record-draft', $event)"
          />

          <button v-if="selectedDate !== todayDate" class="detail-reset" type="button" @click="$emit('show-current-date')">回到最近可用日 <IconMark name="arrow" /></button>
        </aside>
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
