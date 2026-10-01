<script setup>
import { computed, ref } from 'vue'

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

const recordedSuggestions = computed(() => new Set(
  props.selectedRecords
    .filter(record => record.kind === 'action' && record.status !== 'skipped')
    .map(record => record.content)
))

function isQuickRecordSaved(item) {
  return recordedSuggestions.value.has(item)
}

function statusText(status) {
  return { done: '已完成', doing: '进行中', skipped: '已跳过' }[status] || '已记录'
}

function updateDraft(field, value) {
  emit('update-record-draft', { [field]: value })
}

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

          <section class="actual-records" aria-labelledby="actual-record-title">
            <div class="actual-records-head">
              <div>
                <span class="detail-section-kicker">KEEP A TRACE</span>
                <h4 id="actual-record-title">{{ selectedDate === todayDate ? '今天实际做了什么' : '这天实际做了什么' }}</h4>
              </div>
              <span class="actual-count">{{ selectedRecords.length }} 条</span>
            </div>
            <p class="actual-records-intro">把建议和真实发生的事并排保存，日后才能看见自己的节奏。</p>

            <div v-if="selectedRecords.length" class="actual-record-list">
              <article v-for="record in selectedRecords" :key="record.id" class="actual-record-item">
                <div class="actual-record-meta">
                  <span class="record-kind" :class="`kind-${record.kind}`">{{ record.kind === 'decision' ? '决策' : '行动' }}</span>
                  <span class="record-status" :class="`status-${record.status}`">{{ statusText(record.status) }}</span>
                  <button class="record-delete" type="button" @click.stop="$emit('remove-record', record)">删除</button>
                </div>
                <p>{{ record.content }}</p>
                <small v-if="record.note">{{ record.note }}</small>
              </article>
            </div>
            <p v-else class="actual-record-empty">还没有记录。可以从下面的建议开始，也可以写下一件今天真实发生的事。</p>

            <div v-if="selectedEntry.suitable?.length" class="quick-records">
              <div class="quick-records-head"><span>从今日建议记一笔</span><small>已经做过的可以直接加入</small></div>
              <button
                v-for="item in selectedEntry.suitable"
                :key="item"
                type="button"
                class="quick-record-button"
                :class="{ recorded: isQuickRecordSaved(item) }"
                :disabled="isQuickRecordSaved(item) || savingRecord"
                @click="$emit('quick-record', item)"
              >
                <span>{{ item }}</span><b>{{ isQuickRecordSaved(item) ? '已记录' : '＋ 已做' }}</b>
              </button>
            </div>

            <button v-if="!showRecordForm" class="record-add-button" type="button" @click="$emit('open-record-form')">
              <span>＋</span> 记录一件事 / 一个决定
            </button>

            <form v-else class="record-form" :aria-describedby="recordError ? 'record-error' : undefined" @submit.prevent="$emit('save-record')">
              <div class="record-form-head">
                <span>新记录</span>
                <button type="button" @click="$emit('close-record-form')">收起</button>
              </div>
              <div class="record-form-grid">
                <label><span>记录类型</span><select :value="recordDraft.kind" @change="updateDraft('kind', $event.target.value)"><option value="action">行动</option><option value="decision">决策</option></select></label>
                <label><span>当前状态</span><select :value="recordDraft.status" @change="updateDraft('status', $event.target.value)"><option value="done">已完成</option><option value="doing">进行中</option><option value="skipped">跳过</option></select></label>
              </div>
              <label class="record-form-field"><span>实际发生了什么</span><textarea :value="recordDraft.content" rows="3" maxlength="240" placeholder="例如：完成了今天最重要的一件事" @input="updateDraft('content', $event.target.value)"></textarea></label>
              <label class="record-form-field"><span>结果 / 备注（可选）</span><input :value="recordDraft.note" maxlength="240" placeholder="例如：比预想顺利，明天继续细化" @input="updateDraft('note', $event.target.value)"></label>
              <div class="record-form-actions">
                <button class="secondary-button" type="button" @click="$emit('close-record-form')">取消</button>
                <button class="primary-button" type="submit" :disabled="savingRecord" :aria-busy="savingRecord">{{ savingRecord ? '保存中…' : '保存记录' }}</button>
              </div>
              <p v-if="recordError" id="record-error" class="record-error" role="alert" aria-live="assertive">{{ recordError }}</p>
            </form>
            <p v-if="recordFeedback" class="record-feedback" role="status" aria-live="polite">{{ recordFeedback }}</p>
            <p class="record-storage-note"><i></i>{{ recordSource === 'api' ? '已同步到你的账号' : '当前暂存于本设备' }}</p>
          </section>

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
