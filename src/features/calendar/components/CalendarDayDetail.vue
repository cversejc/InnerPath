<script setup>
import { ref } from 'vue'
import ActionRecordsSection from './ActionRecordsSection.vue'

defineProps({
  actionClimate: { type: Object, required: true },
  hiddenGuidanceCount: { type: Number, default: 0 },
  isMobileLayout: { type: Boolean, default: false },
  mobileDetailOpen: { type: Boolean, default: false },
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
  visibleUnsuitable: { type: Array, default: () => [] }
})

const emit = defineEmits([
  'close-mobile-detail',
  'detail-keydown',
  'close-record-form',
  'open-record-form',
  'quick-record',
  'remove-record',
  'save-record',
  'show-current-date',
  'toggle-guidance',
  'update-record-draft'
])

const dayDetail = ref(null)

function focusCloseButton() {
  dayDetail.value?.querySelector('.detail-close')?.focus()
}

function focusContainer() {
  dayDetail.value?.focus()
}

function getFocusableItems() {
  return Array.from(dayDetail.value?.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
  ) || [])
}

defineExpose({ focusCloseButton, focusContainer, getFocusableItems })
</script>

<template>
  <aside
    ref="dayDetail"
    class="paper-card day-detail"
    :class="{ 'is-open': mobileDetailOpen }"
    :role="isMobileLayout && mobileDetailOpen ? 'dialog' : 'complementary'"
    :aria-modal="isMobileLayout && mobileDetailOpen ? 'true' : undefined"
    aria-labelledby="day-detail-title"
    tabindex="-1"
    @keydown="emit('detail-keydown', $event)"
  >
    <button class="detail-close" type="button" aria-label="关闭日期详情" @click="emit('close-mobile-detail')"><IconMark name="close" /></button>
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
    <button v-if="hiddenGuidanceCount" class="guidance-toggle" type="button" @click="emit('toggle-guidance')">
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

    <button v-if="selectedDate !== todayDate" class="detail-reset" type="button" @click="emit('show-current-date')">回到最近可用日 <IconMark name="arrow" /></button>
  </aside>
</template>
