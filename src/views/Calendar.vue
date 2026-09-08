<template>
  <div class="page-shell calendar-page">
    <BrandNav />

    <main v-if="loading" class="calendar-empty-state">
      <div class="container"><h1>正在加载你的个性化日历…</h1></div>
    </main>

    <main v-else-if="!calendar || !days.length" class="calendar-empty-state">
      <div class="container paper-card">
        <span class="seal-badge">PERSONAL TIMEZONE</span>
        <h1>等待管理员维护你的日历</h1>
        <p>你的个性化决策日历发布后，会在这里显示。</p>
      </div>
    </main>

    <main v-else>
      <section class="calendar-hero">
        <div class="container calendar-hero-inner">
          <div class="calendar-hero-copy">
            <p class="section-kicker">TE / DECISION TIMING</p>
            <p class="calendar-overline">{{ meta.subtitle }}</p>
            <h1>{{ meta.title }}</h1>
            <p class="calendar-hero-intro">{{ meta.intro }}</p>
            <div class="calendar-hero-meta">
              <span class="hero-chip hero-chip-date">{{ meta.dateLabel }}</span>
              <span v-if="meta.pillars" class="hero-chip">{{ meta.pillars }}</span>
              <span class="hero-chip hero-chip-rhythm">{{ meta.rhythm }}</span>
              <span v-if="calendarSource === 'mock'" class="hero-chip hero-chip-demo">示例数据 · 发布后自动替换</span>
            </div>
          </div>

          <div class="orbit-card" aria-label="个人日历节奏图示">
            <div class="orbit-ring orbit-ring-outer">
              <span class="orbit-glyph orbit-glyph-top">观</span>
              <span class="orbit-glyph orbit-glyph-right">行</span>
              <span class="orbit-glyph orbit-glyph-bottom">息</span>
              <span class="orbit-glyph orbit-glyph-left">记</span>
              <div class="orbit-ring orbit-ring-inner">
                <div class="orbit-core"><span>辰</span><strong>鉴</strong></div>
              </div>
            </div>
            <div class="orbit-caption">
              <span class="orbit-caption-label">辰鉴 · 本月北极星</span>
              <strong>让行动服从于时机</strong>
              <span>先看见，再决定下一步。</span>
            </div>
          </div>
        </div>
      </section>

      <section class="section-band calendar-overview">
        <div class="container">
          <div class="calendar-section-heading overview-heading">
            <div>
              <p class="section-kicker">MONTHLY OVERVIEW</p>
              <h2 class="section-title">这个月，不急着证明自己在前进</h2>
            </div>
            <p class="section-desc">这张日历像一张低声运转的后台地图：表面动作不多，判断、整合与等待都在发生。</p>
          </div>

          <div class="overview-grid">
            <article class="paper-card overview-story">
              <div class="card-ornament">「 {{ calendar.title }} · 总览 」</div>
              <p v-for="paragraph in meta.overview" :key="paragraph">{{ paragraph }}</p>
              <p class="overview-emphasis">核心节奏：{{ meta.rhythm }}</p>
            </article>

            <div class="overview-side">
              <article class="paper-card focus-card">
                <span class="mini-label">本月只做三件事</span>
                <ol>
                  <li><span>01</span>把辰鉴的产品框架落实到纸面或可交付文档。</li>
                  <li><span>02</span>积累至少3—5个真实的决策日志。</li>
                  <li><span>03</span>与导师的邮件沟通闭环，等待回复即可。</li>
                </ol>
              </article>
              <div class="phase-progress" aria-label="本月四个能量阶段">
                <div class="phase-progress-head"><span>月度节奏</span><strong>4 个阶段</strong></div>
                <div class="phase-progress-bar">
                  <span v-for="phase in phases" :key="phase.id" :class="`phase-progress-${phase.tone}`"></span>
                </div>
                <div class="phase-progress-labels"><span>记录</span><span>表达</span><span>休整</span><span>调整</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

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
                <button class="today-button" type="button" @click="showCurrentDate">回到当前聚焦 <span>↗</span></button>
              </header>

              <div class="calendar-weekdays" aria-hidden="true">
                <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
              </div>

              <div class="calendar-grid">
                <template v-for="cell in calendarCells" :key="cell.key">
                  <div v-if="cell.empty" class="calendar-empty" aria-hidden="true"></div>
                  <button
                    v-else
                    type="button"
                    class="date-cell"
                    :class="[`tone-${cell.tone}`, { selected: selectedDate === cell.date, 'is-today': cell.isCurrentDay }]"
                    :aria-label="`${cell.month}月${cell.day}日，${cell.statusLabel}${cell.recordCount ? `，已有${cell.recordCount}条记录` : ''}`"
                    :aria-selected="selectedDate === cell.date"
                    @click="selectDate(cell.date)"
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

              <button v-if="!mobileDetailOpen" class="mobile-detail-launch" type="button" @click="mobileDetailOpen = true">
                查看 {{ selectedDay.month }}月{{ selectedDay.day }}日的建议与记录 <span>↗</span>
              </button>
            </section>

            <aside class="paper-card day-detail" :class="{ 'is-open': mobileDetailOpen }" aria-live="polite">
              <button class="detail-close" type="button" aria-label="关闭日期详情" @click="mobileDetailOpen = false">×</button>
              <div class="detail-header">
                <div>
                  <span class="detail-kicker">{{ selectedEntry.isPhase ? 'PHASE NAVIGATION' : 'DAY NAVIGATION' }}</span>
                  <h3>{{ selectedDay.month }}月{{ selectedDay.day }}日 <small>星期{{ selectedDay.weekday }}</small></h3>
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
              <p class="detail-summary">{{ selectedEntry.isPhase ? selectedEntry.summary : `这一日适合把“${selectedEntry.keyword}”放在第一位。` }}</p>

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
              <button v-if="hiddenGuidanceCount" class="guidance-toggle" type="button" @click="showFullGuidance = !showFullGuidance">
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
                      <button class="record-delete" type="button" @click.stop="removeDecisionLog(record)">删除</button>
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
                    @click="quickRecord(item)"
                  >
                    <span>{{ item }}</span><b>{{ isQuickRecordSaved(item) ? '已记录' : '＋ 已做' }}</b>
                  </button>
                </div>

                <button v-if="!showRecordForm" class="record-add-button" type="button" @click="openRecordForm">
                  <span>＋</span> 记录一件事 / 一个决定
                </button>

                <form v-else class="record-form" @submit.prevent="saveDecisionLog">
                  <div class="record-form-head">
                    <span>新记录</span>
                    <button type="button" @click="closeRecordForm">收起</button>
                  </div>
                  <div class="record-form-grid">
                    <label><span>记录类型</span><select v-model="recordDraft.kind"><option value="action">行动</option><option value="decision">决策</option></select></label>
                    <label><span>当前状态</span><select v-model="recordDraft.status"><option value="done">已完成</option><option value="doing">进行中</option><option value="skipped">跳过</option></select></label>
                  </div>
                  <label class="record-form-field"><span>实际发生了什么</span><textarea v-model.trim="recordDraft.content" rows="3" maxlength="240" placeholder="例如：完成了产品首页第一版文案"></textarea></label>
                  <label class="record-form-field"><span>结果 / 备注（可选）</span><input v-model.trim="recordDraft.note" maxlength="240" placeholder="例如：比预想顺利，明天继续细化"></label>
                  <div class="record-form-actions">
                    <button class="secondary-button" type="button" @click="closeRecordForm">取消</button>
                    <button class="primary-button" type="submit" :disabled="savingRecord">{{ savingRecord ? '保存中…' : '保存记录' }}</button>
                  </div>
                  <p v-if="recordError" class="record-error">{{ recordError }}</p>
                </form>
                <p v-if="recordFeedback" class="record-feedback">{{ recordFeedback }}</p>
                <p class="record-storage-note"><i></i>{{ recordSource === 'api' ? '已同步到你的账号' : '当前暂存于本设备' }}</p>
              </section>

              <button v-if="selectedDate !== todayDate" class="detail-reset" type="button" @click="showCurrentDate">回到最近可用日 <span>→</span></button>
            </aside>
          </div>

          <div class="phase-rail" aria-label="月度能量阶段">
            <button v-for="phase in phases" :key="phase.id" type="button" class="phase-card" :class="[`tone-${phase.tone}`, { active: selectedEntry.phaseId === phase.id }]" @click="selectDate(phase.startDate)">
              <span class="phase-card-index">0{{ phases.indexOf(phase) + 1 }}</span>
              <span class="phase-card-copy"><strong>{{ phase.label }}</strong><small>{{ phase.dateRange }}</small></span>
              <span class="phase-card-arrow">↗</span>
            </button>
          </div>
        </div>
      </section>

      <section class="section-band decision-section">
        <div class="container">
          <div class="calendar-section-heading compact-heading">
            <div><p class="section-kicker">DECISION WINDOWS</p><h2 class="section-title">本月关键决策节点</h2></div>
            <p class="section-desc">不是每一天都需要完成大事。把重要动作交给真正支持它的窗口。</p>
          </div>
          <div class="decision-table paper-card">
            <div class="decision-row decision-head"><span>日期</span><span>日柱</span><span>色块</span><span>适合决策类型</span></div>
            <button v-for="node in decisionNodes" :key="node.date" type="button" class="decision-row" @click="selectDecisionNode(node)">
              <span><strong>{{ node.date }}</strong></span>
              <span class="node-pillar">{{ node.pillar }}</span>
              <span><i class="legend-dot" :class="`legend-dot-${node.tone}`"></i></span>
              <span class="node-type">{{ node.type }} <b>↗</b></span>
            </button>
          </div>
        </div>
      </section>

      <section class="section-band record-section">
        <div class="container">
          <div class="calendar-section-heading compact-heading">
            <div><p class="section-kicker">KEEP A TRACE</p><h2 class="section-title">把这个月，留下一点可回看的证据</h2></div>
            <p class="section-desc">日期详情已经把“适合做什么”和“实际做了什么”放在一起；这里保留几种适合长期坚持的记录方式。</p>
          </div>
          <div class="record-grid">
            <article v-for="prompt in recordPrompts" :key="prompt.index" class="paper-card record-card">
              <span class="record-index">{{ prompt.index }}</span>
              <h3>{{ prompt.title }}</h3>
              <p>{{ prompt.text }}</p>
              <span class="record-line"></span>
            </article>
          </div>
          <div class="caution-strip paper-card">
            <span class="caution-seal">每日<br />提醒</span>
            <div><strong>这个月不需要做到“完美交付”</strong><p>{{ cautionNotes[2] }}</p></div>
            <span class="caution-mark">辰鉴</span>
          </div>
        </div>
      </section>
    </main>

    <BrandFooter />

    <div v-if="mobileDetailOpen" class="detail-scrim" @click="mobileDetailOpen = false"></div>
  </div>
</template>

<script>
import { authState } from '../stores/auth'
import {
  createDecisionLog,
  deleteDecisionLog,
  getMyCalendars,
  getMyDecisionLogs
} from '../utils/businessService'
import {
  calendarMeta as mockCalendarMeta,
  cautionNotes as mockCautionNotes,
  createCalendarDays as createMockCalendarDays,
  decisionNodes as mockDecisionNodes,
  phaseDefinitions as mockPhaseDefinitions,
  recordPrompts as mockRecordPrompts
} from '../data/decisionCalendar'

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const DECISION_LOG_STORAGE_KEY = 'innerseek:decision-logs'

function createRecordDraft() {
  return {
    kind: 'action',
    status: 'done',
    content: '',
    note: ''
  }
}

function parseDateKey(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(date) {
  const pad = value => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function isToday(dateKey) {
  return formatDateKey(new Date()) === dateKey
}

function createMockCalendar() {
  return {
    id: 'demo-calendar',
    user_id: null,
    title: mockCalendarMeta.title,
    start_date: mockCalendarMeta.startDate,
    end_date: mockCalendarMeta.endDate,
    status: 'published',
    entries: createMockCalendarDays().map((entry, index) => ({
      id: `demo-entry-${index + 1}`,
      entry_date: entry.date,
      day_pillar: entry.dayPillar || null,
      tone: entry.tone || null,
      status_label: entry.statusLabel || null,
      keyword: entry.keyword || null,
      summary: entry.summary || null,
      suitable: entry.suitable || [],
      unsuitable: entry.unsuitable || [],
      time_window: entry.timeWindow || null,
      phase_id: entry.phaseId || null,
      phase_label: entry.phaseLabel || null,
      is_phase: entry.isPhase || false
    }))
  }
}

function dateKeyFromLabel(label, year) {
  const [, month, day] = label.match(/(\d+)月(\d+)日/) || []
  if (!month || !day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

export default {
  name: 'Calendar',
  data() {
    return {
      loading: true,
      calendar: null,
      calendarSource: 'api',
      meta: {},
      phases: [],
      days: [],
      weekdays: ['一', '二', '三', '四', '五', '六', '日'],
      selectedDate: null,
      todayDate: null,
      mobileDetailOpen: false,
      decisionNodes: [],
      recordPrompts: [],
      cautionNotes: ['', '', '日历内容由辰鉴管理员维护'],
      decisionLogs: [],
      recordSource: 'local',
      showRecordForm: false,
      showFullGuidance: false,
      recordDraft: createRecordDraft(),
      recordError: '',
      recordFeedback: '',
      savingRecord: false
    }
  },
  computed: {
    selectedDay() {
      return this.days.find(day => day.date === this.selectedDate) || this.days[0] || {}
    },
    selectedEntry() {
      return this.selectedDay
    },
    actionClimate() {
      const climateByTone = {
        green: { label: '推进窗口', caption: '适合把已经想清楚的事做成。', position: 84 },
        'green-yellow': { label: '先推进，再收束', caption: '上午打开行动，后半天留一点余地。', position: 72 },
        'yellow-green': { label: '先准备，再行动', caption: '先把信息理顺，下午再迈出下一步。', position: 58 },
        yellow: { label: '观察与准备', caption: '今天更适合整理判断，而不是急着拍板。', position: 45 },
        'red-yellow': { label: '缓冲后再判断', caption: '先降低消耗，等思路重新变得清楚。', position: 29 },
        red: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 },
        rest: { label: '先收气', caption: '今天更适合减少消耗，为下一次行动留力。', position: 16 }
      }
      return climateByTone[this.selectedEntry.tone] || climateByTone.yellow
    },
    visibleSuitable() {
      return this.showFullGuidance ? this.selectedEntry.suitable : this.selectedEntry.suitable.slice(0, 2)
    },
    visibleUnsuitable() {
      return this.showFullGuidance ? this.selectedEntry.unsuitable : this.selectedEntry.unsuitable.slice(0, 1)
    },
    hiddenGuidanceCount() {
      if (this.showFullGuidance) return 0
      return Math.max(0, this.selectedEntry.suitable.length - 2) + Math.max(0, this.selectedEntry.unsuitable.length - 1)
    },
    rhythmSegments() {
      const rhythmByTone = {
        green: [['上午', '聚焦', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
        'green-yellow': [['上午', '表达', 'green'], ['下午', '推进', 'green'], ['晚上', '收束', 'yellow']],
        'yellow-green': [['上午', '观察', 'yellow'], ['下午', '启动', 'green'], ['晚上', '整理', 'yellow']],
        yellow: [['上午', '观察', 'yellow'], ['下午', '准备', 'yellow'], ['晚上', '轻推', 'green']],
        'red-yellow': [['上午', '缓冲', 'red'], ['下午', '整理', 'yellow'], ['晚上', '收气', 'red']],
        red: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']],
        rest: [['上午', '收气', 'red'], ['下午', '整理', 'yellow'], ['晚上', '休息', 'red']]
      }
      return (rhythmByTone[this.selectedEntry.tone] || rhythmByTone.yellow).map(([period, label, tone]) => ({ period, label, tone }))
    },
    selectedRecords() {
      return this.decisionLogs.filter(record => record.date === this.selectedDate)
    },
    recordCountByDate() {
      return this.decisionLogs.reduce((counts, record) => {
        counts[record.date] = (counts[record.date] || 0) + 1
        return counts
      }, {})
    },
    monthRecordCount() {
      return this.decisionLogs.filter(record => this.days.some(day => day.date === record.date)).length
    },
    monthRecordDays() {
      return new Set(this.decisionLogs.filter(record => this.days.some(day => day.date === record.date)).map(record => record.date)).size
    },
    calendarLabel() {
      if (!this.calendar) return ''
      const start = this.calendar.start_date || this.days[0]?.date
      const end = this.calendar.end_date || this.days[this.days.length - 1]?.date
      if (!start || !end) return '个人日历'
      return `${start.slice(0, 7).replace('-', ' / ')}—${end.slice(0, 7).replace('-', ' / ')}`
    },
    calendarCells() {
      if (!this.days.length) return []
      const firstDate = parseDateKey(this.days[0].date)
      const leading = (firstDate.getDay() + 6) % 7
      const trailing = (7 - ((leading + this.days.length) % 7)) % 7
      const emptyCells = Array.from({ length: leading + trailing }, (_, index) => ({
        key: `empty-${index}`,
        empty: true
      }))
      return [
        ...emptyCells.slice(0, leading),
        ...this.days.map(day => ({
          ...day,
          key: day.date,
          isCurrentDay: isToday(day.date),
          recordCount: this.recordCountByDate[day.date] || 0
        })),
        ...emptyCells.slice(leading)
      ]
    }
  },
  async mounted() {
    window.addEventListener('keydown', this.handleEscape)
    await this.loadCalendar()
    await this.loadDecisionLogs()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleEscape)
  },
  methods: {
    async loadCalendar() {
      try {
        const response = await getMyCalendars()
        const publishedCalendar = response.items?.find(item => item.entries?.length) || null
        this.applyCalendar(publishedCalendar || createMockCalendar(), publishedCalendar ? 'api' : 'mock')
      } catch (error) {
        this.applyCalendar(createMockCalendar(), 'mock')
      } finally {
        this.loading = false
      }
    },
    applyCalendar(calendar, source) {
      this.calendar = calendar
      this.calendarSource = source
      this.days = (calendar.entries || []).map(entry => {
        const entryDate = entry.entry_date || entry.date
        if (!entryDate) return null
        const date = parseDateKey(entryDate)
        return {
          ...entry,
          date: entryDate,
          month: date.getMonth() + 1,
          day: date.getDate(),
          weekday: weekdays[date.getDay()],
          dayPillar: entry.day_pillar || entry.dayPillar || '',
          statusLabel: entry.status_label || entry.statusLabel || '',
          shortLabel: entry.keyword || entry.shortLabel || entry.status_label || entry.statusLabel || '查看',
          phaseId: entry.phase_id || entry.phaseId || entry.tone || 'default',
          phaseLabel: entry.phase_label || entry.phaseLabel || entry.status_label || entry.statusLabel || entry.tone || '',
          timeWindow: entry.time_window || entry.timeWindow || '按你的节奏安排，给决定留出换气空间。',
          suitable: entry.suitable || [],
          unsuitable: entry.unsuitable || [],
          isPhase: entry.is_phase ?? entry.isPhase ?? false
        }
      }).filter(Boolean)
      const startDate = calendar.start_date || this.days[0]?.date || ''
      const year = startDate.slice(0, 4)
      this.meta = source === 'mock'
        ? mockCalendarMeta
        : {
            title: calendar.title,
            subtitle: 'PERSONAL TIMEZONE',
            dateLabel: `${startDate} — ${calendar.end_date || this.days[this.days.length - 1]?.date || ''}`,
            pillars: '',
            rhythm: '少说，多做，多记录',
            intro: '这是一张由辰鉴为你维护的个性化决策时机参照系。',
            overview: []
          }
      this.todayDate = this.days.find(day => isToday(day.date))?.date || this.days[0]?.date || null
      this.selectedDate = this.todayDate
      this.decisionNodes = source === 'mock'
        ? mockDecisionNodes.map(node => ({ ...node, dateKey: dateKeyFromLabel(node.date, year) }))
        : this.days.map(day => ({
            date: `${day.month}月${day.day}日`,
            dateKey: day.date,
            pillar: day.dayPillar || '—',
            tone: day.tone || 'yellow',
            type: day.keyword || day.statusLabel || '查看详情'
          }))
      this.phases = source === 'mock' ? mockPhaseDefinitions : this.buildPhases()
      this.recordPrompts = source === 'mock' ? mockRecordPrompts : []
      this.cautionNotes = source === 'mock' ? mockCautionNotes : ['', '', '日历内容由辰鉴管理员维护']
      this.mobileDetailOpen = !(window.matchMedia('(max-width: 900px)').matches)
    },
    buildPhases() {
      const grouped = []
      for (const day of this.days) {
        const existing = grouped.find(phase => phase.id === day.phaseId)
        if (existing) {
          existing.endDate = day.date
          existing.dateRange = `${existing.startDate}—${existing.endDate}`
        } else {
          grouped.push({
            id: day.phaseId,
            label: day.phaseLabel || day.shortLabel,
            tone: day.tone || 'yellow',
            startDate: day.date,
            endDate: day.date,
            dateRange: day.date
          })
        }
      }
      return grouped
    },
    selectDate(date) {
      this.selectedDate = date
      this.closeRecordForm()
      this.recordFeedback = ''
      this.showFullGuidance = false
      if (window.matchMedia('(max-width: 900px)').matches) {
        this.mobileDetailOpen = true
      }
    },
    selectDecisionNode(node) {
      this.selectDate(node.dateKey || this.selectedDate)
    },
    showCurrentDate() {
      if (this.todayDate) this.selectDate(this.todayDate)
      this.mobileDetailOpen = true
    },
    getRecordStorageKey() {
      const userKey = authState.user?.id || 'guest'
      return `${DECISION_LOG_STORAGE_KEY}:${userKey}`
    },
    normalizeDecisionLog(log) {
      return {
        id: log.id ?? log.localId ?? `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        date: log.log_date || log.date,
        kind: log.kind || log.type || 'action',
        status: log.status || 'done',
        content: log.content || '',
        note: log.note || '',
        createdAt: log.created_at || log.createdAt || new Date().toISOString()
      }
    },
    readLocalDecisionLogs() {
      try {
        const stored = window.localStorage.getItem(this.getRecordStorageKey())
        const parsed = stored ? JSON.parse(stored) : []
        return Array.isArray(parsed) ? parsed.map(record => this.normalizeDecisionLog(record)).filter(record => record.date && record.content) : []
      } catch (error) {
        return []
      }
    },
    persistLocalDecisionLogs(records = this.decisionLogs) {
      try {
        window.localStorage.setItem(this.getRecordStorageKey(), JSON.stringify(records))
      } catch (error) {
        // Local storage may be unavailable in private browsing; the page can still keep the in-memory record.
      }
    },
    async loadDecisionLogs() {
      const localRecords = this.readLocalDecisionLogs()
      try {
        const response = await getMyDecisionLogs({
          start_date: this.days[0]?.date,
          end_date: this.days[this.days.length - 1]?.date
        })
        this.decisionLogs = (response.items || []).map(record => this.normalizeDecisionLog(record)).filter(record => record.date && record.content)
        this.recordSource = 'api'
      } catch (error) {
        this.decisionLogs = localRecords
        this.recordSource = 'local'
      }
    },
    async persistDecisionLog(payload) {
      const localRecord = this.normalizeDecisionLog({
        ...payload,
        date: this.selectedDate,
        localId: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      })

      if (this.recordSource === 'api') {
        try {
          const response = await createDecisionLog({
            log_date: this.selectedDate,
            kind: payload.kind,
            status: payload.status,
            content: payload.content,
            note: payload.note || null
          })
          this.decisionLogs = [...this.decisionLogs, this.normalizeDecisionLog(response)]
          return
        } catch (error) {
          this.recordSource = 'local'
        }
      }

      this.decisionLogs = [...this.decisionLogs, localRecord]
      this.persistLocalDecisionLogs()
    },
    async loadRecordAndGiveFeedback(payload, message) {
      this.savingRecord = true
      this.recordError = ''
      try {
        await this.persistDecisionLog(payload)
        this.recordFeedback = message
      } catch (error) {
        this.recordError = '记录没有保存成功，请稍后再试。'
      } finally {
        this.savingRecord = false
      }
    },
    openRecordForm() {
      this.recordError = ''
      this.recordFeedback = ''
      this.showRecordForm = true
    },
    closeRecordForm() {
      this.showRecordForm = false
      this.recordError = ''
      this.recordDraft = createRecordDraft()
    },
    async saveDecisionLog() {
      const content = this.recordDraft.content.trim()
      if (!content) {
        this.recordError = '先写下今天实际发生的事。'
        return
      }

      await this.loadRecordAndGiveFeedback({
        kind: this.recordDraft.kind,
        status: this.recordDraft.status,
        content,
        note: this.recordDraft.note.trim()
      }, '已把这件事留在今天。')

      if (!this.recordError) {
        this.recordDraft = createRecordDraft()
        this.showRecordForm = false
      }
    },
    isQuickRecordSaved(item) {
      return this.selectedRecords.some(record => record.kind === 'action' && record.content === item && record.status !== 'skipped')
    },
    async quickRecord(item) {
      if (this.isQuickRecordSaved(item)) return
      await this.loadRecordAndGiveFeedback({ kind: 'action', status: 'done', content: item, note: '' }, '已把这条建议记为今天做过的事。')
    },
    statusText(status) {
      return { done: '已完成', doing: '进行中', skipped: '已跳过' }[status] || '已记录'
    },
    async removeDecisionLog(record) {
      if (!window.confirm('确定删除这条记录吗？')) return
      this.recordError = ''
      try {
        if (typeof record.id === 'number') {
          await deleteDecisionLog(record.id)
        }
        this.decisionLogs = this.decisionLogs.filter(item => item.id !== record.id)
        if (this.recordSource === 'local' || typeof record.id !== 'number') this.persistLocalDecisionLogs()
        this.recordFeedback = '记录已移除。'
      } catch (error) {
        this.recordError = '删除没有成功，请稍后再试。'
      }
    },
    handleEscape(event) {
      if (event.key === 'Escape') this.mobileDetailOpen = false
    }
  }
}
</script>

<style scoped>
.calendar-page {
  --calendar-ink: #2e251d;
  --calendar-muted: #806e5f;
  --calendar-line: rgba(139, 90, 20, 0.16);
  --calendar-green: #658f73;
  --calendar-yellow: #bd9550;
  --calendar-red: #b45d58;
  background: linear-gradient(180deg, rgba(255, 250, 240, 0.38), rgba(234, 217, 191, 0.14));
}

.calendar-empty-state {
  display: grid;
  min-height: 70vh;
  place-items: center;
  padding: 60px 0;
  background: linear-gradient(180deg, rgba(255, 250, 240, 0.7), rgba(234, 217, 191, 0.16));
}

.calendar-empty-state .paper-card {
  width: min(100% - 32px, 720px);
  padding: 42px;
  text-align: center;
}

.calendar-empty-state h1 {
  margin: 16px 0 12px;
  color: var(--calendar-ink, #2e251d);
}

.calendar-empty-state p {
  color: var(--calendar-muted, #806e5f);
}

.calendar-hero {
  position: relative;
  overflow: hidden;
  min-height: 560px;
  background:
    radial-gradient(circle at 76% 24%, rgba(217, 186, 98, 0.24), transparent 25%),
    radial-gradient(circle at 10% 100%, rgba(111, 159, 147, 0.16), transparent 34%),
    linear-gradient(130deg, rgba(255, 250, 240, 0.72), rgba(247, 235, 216, 0.72) 55%, rgba(232, 215, 190, 0.68));
}

.calendar-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.44;
  background:
    linear-gradient(115deg, transparent 0 48%, rgba(184, 92, 80, 0.08) 49%, transparent 50%),
    linear-gradient(65deg, transparent 0 65%, rgba(139, 90, 20, 0.06) 66%, transparent 67%),
    radial-gradient(ellipse at 46% 104%, rgba(48, 61, 55, 0.24) 0 18%, transparent 19%);
}

.calendar-hero::after {
  content: '辰鉴';
  position: absolute;
  right: -24px;
  bottom: -86px;
  color: rgba(158, 63, 53, 0.08);
  font-size: 220px;
  font-weight: 900;
  letter-spacing: -0.16em;
  line-height: 1;
  transform: rotate(-12deg);
  pointer-events: none;
}

.calendar-hero-inner {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr);
  align-items: center;
  gap: clamp(30px, 6vw, 96px);
  min-height: 560px;
  padding-top: 58px;
  padding-bottom: 70px;
}

.calendar-hero-copy {
  max-width: 700px;
}

.calendar-overline {
  margin-top: 22px;
  color: var(--cinnabar-deep);
  font-family: 'Manrope', 'PingFang SC', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.13em;
}

.calendar-hero h1 {
  margin-top: 14px;
  color: var(--calendar-ink);
  font-size: clamp(43px, 7vw, 76px);
  font-weight: 900;
  line-height: 1.06;
  letter-spacing: 0.015em;
}

.calendar-hero h1 span {
  color: var(--cinnabar);
}

.calendar-hero h1 em {
  color: var(--cinnabar-deep);
  font-style: normal;
}

.calendar-hero-intro {
  max-width: 560px;
  margin-top: 25px;
  color: var(--calendar-muted);
  font-size: 18px;
  line-height: 1.85;
}

.calendar-hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 31px;
}

.hero-chip {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  border: 1px solid rgba(139, 90, 20, 0.16);
  border-radius: 999px;
  padding: 0 13px;
  background: rgba(255, 252, 245, 0.54);
  color: var(--calendar-muted);
  font-family: 'Manrope', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.hero-chip-date {
  border-color: rgba(184, 92, 80, 0.25);
  color: var(--cinnabar-deep);
}

.hero-chip-rhythm {
  background: rgba(111, 159, 147, 0.13);
  color: #4c7569;
}

.hero-chip-demo {
  border-style: dashed;
  border-color: rgba(184, 92, 80, 0.34);
  background: rgba(255, 240, 223, 0.72);
  color: var(--cinnabar-deep);
}

.orbit-card {
  justify-self: end;
  width: min(100%, 390px);
  padding: 26px 28px 24px;
  border: 1px solid rgba(139, 90, 20, 0.15);
  border-radius: 28px;
  background: rgba(255, 252, 245, 0.47);
  box-shadow: 0 26px 70px -38px rgba(79, 51, 30, 0.56), inset 0 1px 0 rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(15px);
}

.orbit-ring {
  position: relative;
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  border-radius: 50%;
}

.orbit-ring-outer {
  width: min(100%, 275px);
  margin: 0 auto;
  border: 1px solid rgba(184, 92, 80, 0.32);
  background:
    repeating-conic-gradient(from 0deg, rgba(139, 90, 20, 0.1) 0deg 1deg, transparent 1deg 15deg),
    radial-gradient(circle, rgba(255, 252, 245, 0.65) 0 46%, transparent 47%);
  box-shadow: inset 0 0 0 13px rgba(255, 252, 245, 0.2), 0 16px 40px -26px rgba(139, 90, 20, 0.55);
}

.orbit-ring-outer::before,
.orbit-ring-outer::after {
  content: '';
  position: absolute;
  inset: 25px;
  border: 1px dashed rgba(139, 90, 20, 0.27);
  border-radius: 50%;
}

.orbit-ring-outer::after {
  inset: 53px;
  border-style: solid;
  border-color: rgba(184, 92, 80, 0.18);
}

.orbit-ring-inner {
  width: 128px;
  border: 1px solid rgba(184, 92, 80, 0.34);
  background: rgba(255, 250, 240, 0.75);
  box-shadow: 0 12px 26px -22px rgba(158, 63, 53, 0.85);
}

.orbit-core {
  display: grid;
  place-items: center;
  width: 76px;
  aspect-ratio: 1;
  border: 1px solid rgba(217, 186, 98, 0.75);
  border-radius: 50%;
  background: rgba(255, 252, 245, 0.78);
  color: var(--cinnabar-deep);
  line-height: 1;
}

.orbit-core span { font-size: 17px; }
.orbit-core strong { font-size: 27px; }

.orbit-glyph {
  position: absolute;
  z-index: 2;
  color: var(--cinnabar-deep);
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  font-weight: 800;
}

.orbit-glyph-top { top: 10px; }
.orbit-glyph-right { right: 11px; top: 50%; transform: translateY(-50%); }
.orbit-glyph-bottom { bottom: 10px; }
.orbit-glyph-left { left: 11px; top: 50%; transform: translateY(-50%); }

.orbit-caption {
  display: grid;
  gap: 6px;
  margin-top: 22px;
  text-align: center;
}

.orbit-caption-label,
.month-eyebrow,
.detail-kicker,
.mini-label {
  color: var(--gold-deep);
  font-family: 'Manrope', 'PingFang SC', sans-serif;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.orbit-caption strong { color: var(--calendar-ink); font-size: 17px; }
.orbit-caption > span:last-child { color: var(--calendar-muted); font-size: 13px; }

.calendar-overview,
.decision-section { background: rgba(255, 250, 240, 0.28); }

.calendar-section { background: rgba(255, 252, 245, 0.56); }

.record-section { background: linear-gradient(180deg, rgba(248, 241, 230, 0.56), rgba(234, 217, 191, 0.32)); }

.calendar-section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 30px;
}

.calendar-section-heading .section-desc {
  max-width: 410px;
  margin: 0;
  text-align: right;
}

.overview-heading { align-items: start; }

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(300px, 0.95fr);
  gap: 20px;
}

.overview-story,
.focus-card { padding: 28px; }

.overview-story {
  position: relative;
  overflow: hidden;
}

.overview-story::after {
  content: '酉';
  position: absolute;
  right: -15px;
  bottom: -38px;
  color: rgba(184, 92, 80, 0.08);
  font-size: 170px;
  font-weight: 900;
  line-height: 1;
}

.card-ornament {
  position: relative;
  z-index: 1;
  margin-bottom: 20px;
  color: var(--cinnabar-deep);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.overview-story p {
  position: relative;
  z-index: 1;
  max-width: 650px;
  color: var(--calendar-muted);
  font-size: 16px;
  line-height: 1.95;
}

.overview-story p + p { margin-top: 14px; }

.overview-story .overview-emphasis {
  margin-top: 22px;
  color: var(--cinnabar-deep);
  font-weight: 800;
}

.overview-side { display: grid; gap: 14px; }

.focus-card { background: linear-gradient(145deg, rgba(255, 252, 245, 0.92), rgba(249, 239, 218, 0.68)); }

.focus-card ol { display: grid; gap: 15px; margin-top: 18px; }

.focus-card li {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 10px;
  color: var(--calendar-ink);
  font-size: 14px;
  line-height: 1.65;
}

.focus-card li span {
  color: var(--cinnabar);
  font-family: 'Manrope', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.06em;
}

.phase-progress {
  padding: 17px 19px;
  border: 1px solid rgba(139, 90, 20, 0.13);
  border-radius: var(--radius-card);
  background: rgba(255, 252, 245, 0.48);
}

.phase-progress-head,
.phase-progress-labels { display: flex; justify-content: space-between; gap: 10px; }
.phase-progress-head { color: var(--calendar-muted); font-size: 12px; }
.phase-progress-head strong { color: var(--calendar-ink); font-size: 12px; }

.phase-progress-bar { display: flex; gap: 4px; height: 8px; margin-top: 13px; }
.phase-progress-bar span { flex: 1; border-radius: 999px; }
.phase-progress-yellow { background: #d1ad5e; }
.phase-progress-green { background: #6f9f93; }
.phase-progress-rest { background: linear-gradient(90deg, #d1ad5e, #b45d58); }
.phase-progress-labels { margin-top: 8px; color: var(--calendar-muted); font-size: 10px; }

.calendar-heading-side { display: grid; justify-items: end; gap: 12px; }
.calendar-trace-summary { display: flex; align-items: baseline; gap: 9px; color: var(--calendar-muted); font-size: 12px; }
.calendar-trace-summary strong { color: var(--cinnabar-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 12px; letter-spacing: 0.04em; }
.legend { display: flex; flex-wrap: wrap; justify-content: end; gap: 13px; color: var(--calendar-muted); font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--calendar-muted); }
.legend-dot-green { background: var(--calendar-green); }
.legend-dot-yellow { background: var(--calendar-yellow); }
.legend-dot-red { background: var(--calendar-red); }
.legend-dot-yellow-green { background: linear-gradient(90deg, var(--calendar-yellow), var(--calendar-green)); }
.legend-dot-record { border: 2px solid var(--cinnabar); background: transparent; box-shadow: 0 0 0 2px rgba(184, 92, 80, 0.1); }

.calendar-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.32fr) minmax(330px, 0.68fr);
  align-items: start;
  gap: 20px;
}

.month-board { min-width: 0; padding: 23px; }

.month-board-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 24px;
}

.month-board-head h3 { margin-top: 7px; color: var(--calendar-ink); font-size: 29px; letter-spacing: 0.04em; }
.month-board-head p { margin-top: 4px; color: var(--calendar-muted); font-size: 12px; }

.today-button,
.mobile-detail-launch,
.detail-reset {
  border: 1px solid rgba(184, 92, 80, 0.23);
  border-radius: 999px;
  padding: 9px 13px;
  background: rgba(184, 92, 80, 0.07);
  color: var(--cinnabar-deep);
  font-family: 'Manrope', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
  transition: transform 0.2s ease, background 0.2s ease;
}

.today-button:hover,
.mobile-detail-launch:hover,
.detail-reset:hover { transform: translateY(-1px); background: rgba(184, 92, 80, 0.13); }
.today-button span,
.mobile-detail-launch span,
.detail-reset span { margin-left: 5px; font-size: 14px; }

.calendar-weekdays,
.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; }

.calendar-weekdays { margin-bottom: 8px; }

.calendar-weekdays span {
  padding: 0 4px 4px;
  color: var(--calendar-muted);
  font-family: 'Manrope', 'PingFang SC', sans-serif;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.16em;
  text-align: center;
}

.calendar-empty { min-height: 112px; border: 1px dashed rgba(139, 90, 20, 0.08); border-radius: 14px; }

.date-cell {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 112px;
  flex-direction: column;
  align-items: flex-start;
  border: 1px solid rgba(139, 90, 20, 0.12);
  border-radius: 14px;
  padding: 11px 11px 10px;
  overflow: hidden;
  background: rgba(255, 252, 245, 0.53);
  color: var(--calendar-ink);
  text-align: left;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.date-cell::after {
  content: '';
  position: absolute;
  right: -17px;
  top: -17px;
  width: 48px;
  aspect-ratio: 1;
  border-radius: 50%;
  opacity: 0.35;
  background: currentColor;
}

.date-cell:hover { transform: translateY(-2px); border-color: rgba(184, 92, 80, 0.36); box-shadow: 0 12px 24px -20px rgba(84, 48, 25, 0.8); }
.date-cell.selected { border-color: var(--cinnabar-deep); box-shadow: 0 0 0 3px rgba(184, 92, 80, 0.12), 0 16px 26px -20px rgba(158, 63, 53, 0.76); }

.date-cell.tone-yellow { color: var(--calendar-yellow); background: linear-gradient(145deg, rgba(255, 251, 235, 0.92), rgba(246, 232, 190, 0.42)); }
.date-cell.tone-green { color: var(--calendar-green); background: linear-gradient(145deg, rgba(241, 249, 239, 0.88), rgba(205, 229, 215, 0.42)); }
.date-cell.tone-red { color: var(--calendar-red); background: linear-gradient(145deg, rgba(255, 244, 238, 0.9), rgba(237, 204, 196, 0.42)); }
.date-cell.tone-yellow-green { color: var(--calendar-green); background: linear-gradient(135deg, rgba(247, 235, 195, 0.76) 0 51%, rgba(211, 231, 215, 0.68) 52%); }
.date-cell.tone-red-yellow { color: var(--calendar-yellow); background: linear-gradient(135deg, rgba(239, 207, 199, 0.76) 0 51%, rgba(247, 235, 195, 0.68) 52%); }
.date-cell.tone-green-yellow { color: var(--calendar-green); background: linear-gradient(135deg, rgba(211, 231, 215, 0.76) 0 51%, rgba(247, 235, 195, 0.68) 52%); }
.date-cell.tone-rest { color: var(--calendar-red); background: linear-gradient(135deg, rgba(247, 235, 195, 0.62), rgba(239, 207, 199, 0.64)); }

.date-cell-top { display: flex; align-items: baseline; gap: 5px; color: var(--calendar-ink); }
.date-cell-top strong { font-size: 23px; line-height: 1; }
.date-cell-top em { color: var(--calendar-muted); font-size: 9px; font-style: normal; }
.date-cell-pillar { position: relative; z-index: 1; margin-top: 9px; color: currentColor; font-size: 12px; font-weight: 900; letter-spacing: 0.12em; }
.date-cell-keyword { position: relative; z-index: 1; margin-top: auto; color: var(--calendar-ink); font-size: 12px; font-weight: 800; }
.date-cell-status { position: relative; z-index: 1; max-width: 100%; margin-top: 5px; overflow: hidden; color: var(--calendar-muted); font-size: 9px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.date-cell-record { position: relative; z-index: 1; display: inline-flex; align-items: center; gap: 4px; margin-top: 5px; color: var(--cinnabar-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 8px; font-weight: 900; }
.date-cell-record i { display: inline-block; width: 6px; height: 6px; border: 1px solid var(--cinnabar); border-radius: 50%; background: rgba(184, 92, 80, 0.22); }
.today-mark { position: absolute; right: 9px; bottom: 9px; z-index: 2; color: var(--cinnabar-deep); font-family: 'Manrope', sans-serif; font-size: 9px; font-weight: 900; }
.date-cell.is-today { outline: 2px solid rgba(184, 92, 80, 0.42); outline-offset: -4px; }

.mobile-detail-launch { display: none; width: 100%; margin-top: 12px; }

.day-detail {
  position: sticky;
  top: 88px;
  min-width: 0;
  padding: 25px;
  overflow: hidden;
  background: linear-gradient(155deg, rgba(255, 252, 245, 0.96), rgba(249, 239, 218, 0.82));
}

.day-detail::after {
  content: '时';
  position: absolute;
  right: -22px;
  bottom: -60px;
  color: rgba(111, 159, 147, 0.1);
  font-size: 180px;
  font-weight: 900;
  line-height: 1;
}

.detail-close { display: none; }

.detail-header,
.detail-title-row { position: relative; z-index: 1; display: flex; align-items: start; justify-content: space-between; gap: 12px; }
.detail-header h3 { margin-top: 8px; color: var(--calendar-ink); font-size: 30px; }
.detail-header h3 small { color: var(--calendar-muted); font-size: 12px; font-weight: 500; }

.status-pill { display: inline-flex; max-width: 126px; align-items: center; border-radius: 999px; padding: 7px 10px; color: #fff; font-size: 10px; font-weight: 800; line-height: 1.35; text-align: center; }
.status-pill.tone-yellow { background: var(--calendar-yellow); }
.status-pill.tone-green { background: var(--calendar-green); }
.status-pill.tone-red { background: var(--calendar-red); }
.status-pill.tone-yellow-green, .status-pill.tone-green-yellow { color: #566b45; background: linear-gradient(90deg, #d1ad5e, #92b39a); }
.status-pill.tone-red-yellow { color: #704c32; background: linear-gradient(90deg, #ba6861, #d2ad5c); }
.status-pill.tone-rest { color: #704c32; background: linear-gradient(90deg, #d2ad5c, #ba6861); }

.detail-title-row { align-items: center; margin-top: 18px; }
.detail-pillar { color: var(--cinnabar-deep); font-size: 15px; font-weight: 900; letter-spacing: 0.12em; }
.detail-phase { color: var(--calendar-muted); font-size: 11px; }

.detail-section-kicker { color: var(--gold-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 9px; font-weight: 900; letter-spacing: 0.16em; text-transform: uppercase; }
.day-signal-card { position: relative; z-index: 1; margin-top: 22px; padding: 16px; overflow: hidden; border: 1px solid rgba(184, 92, 80, 0.2); border-radius: 16px; background: linear-gradient(145deg, rgba(255, 252, 245, 0.92), rgba(239, 231, 209, 0.72)); }
.day-signal-card::after { content: '日'; position: absolute; right: -11px; bottom: -31px; color: rgba(184, 92, 80, 0.09); font-size: 104px; font-weight: 900; line-height: 1; }
.day-signal-top { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.day-signal-copy { min-width: 0; }
.day-signal-copy strong { display: block; margin-top: 7px; color: var(--calendar-ink); font-size: 23px; line-height: 1.1; }
.day-signal-copy p { max-width: 220px; margin-top: 6px; color: var(--calendar-muted); font-size: 11px; line-height: 1.6; }
.keyword-stamp { display: grid; flex: 0 0 66px; place-items: center; width: 66px; aspect-ratio: 1; border: 1px solid rgba(184, 92, 80, 0.43); border-radius: 50%; background: rgba(255, 250, 240, 0.72); box-shadow: 0 8px 18px -14px rgba(158, 63, 53, 0.9); transform: rotate(5deg); }
.keyword-stamp strong { color: var(--cinnabar-deep); font-size: 20px; line-height: 1; }
.keyword-stamp span { margin-top: -1px; color: var(--calendar-muted); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 8px; font-weight: 800; letter-spacing: 0.12em; }
.climate-meter { position: relative; z-index: 1; margin-top: 18px; }
.climate-meter-labels { display: flex; justify-content: space-between; color: var(--calendar-muted); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 8px; font-weight: 800; }
.climate-meter-track { position: relative; height: 8px; margin-top: 8px; overflow: visible; border-radius: 999px; background: linear-gradient(90deg, rgba(180, 93, 88, 0.78), rgba(209, 173, 94, 0.78) 48%, rgba(111, 159, 147, 0.82)); }
.climate-meter-fill { position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: rgba(255, 252, 245, 0.54); }
.climate-meter-track > i { position: absolute; top: 50%; width: 17px; height: 17px; border: 3px solid #fffaf0; border-radius: 50%; box-shadow: 0 3px 10px -5px rgba(47, 36, 27, 0.9); transform: translate(-50%, -50%); }
.climate-meter-track > i.tone-green, .climate-meter-track > i.tone-green-yellow { background: var(--calendar-green); }
.climate-meter-track > i.tone-yellow, .climate-meter-track > i.tone-yellow-green { background: var(--calendar-yellow); }
.climate-meter-track > i.tone-red, .climate-meter-track > i.tone-red-yellow, .climate-meter-track > i.tone-rest { background: var(--calendar-red); }
.detail-summary { position: relative; z-index: 1; margin-top: 14px; color: var(--calendar-muted); font-size: 13px; line-height: 1.75; }

.rhythm-strip { position: relative; z-index: 1; margin-top: 17px; padding: 13px; border: 1px solid rgba(111, 159, 147, 0.23); border-radius: 13px; background: rgba(111, 159, 147, 0.08); }
.rhythm-strip-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; color: #4f806f; font-size: 11px; font-weight: 900; }
.rhythm-strip-head small { color: #5b7065; font-size: 9px; font-weight: 500; }
.rhythm-track { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin-top: 10px; }
.rhythm-segment { display: grid; min-height: 45px; align-content: space-between; padding: 7px 8px; border-radius: 9px; }
.rhythm-segment span { color: var(--calendar-muted); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 8px; font-weight: 800; }
.rhythm-segment strong { color: var(--calendar-ink); font-size: 11px; }
.rhythm-green { background: rgba(111, 159, 147, 0.2); }
.rhythm-yellow { background: rgba(217, 186, 98, 0.22); }
.rhythm-red { background: rgba(180, 93, 88, 0.15); }
.rhythm-note { margin-top: 9px; color: #5b7065; font-size: 10px; line-height: 1.6; }

.guidance-grid { position: relative; z-index: 1; display: grid; grid-template-columns: 1.08fr 0.92fr; gap: 8px; margin-top: 15px; }
.guidance-card { min-width: 0; padding: 12px; border: 1px solid transparent; border-radius: 12px; }
.guidance-good { border-color: rgba(111, 159, 147, 0.24); background: rgba(111, 159, 147, 0.09); }
.guidance-bad { border-color: rgba(180, 93, 88, 0.18); background: rgba(180, 93, 88, 0.06); }
.guidance-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--calendar-ink); font-size: 11px; font-weight: 900; }
.guidance-card-head b { display: inline-grid; width: 19px; height: 19px; place-items: center; border-radius: 50%; color: var(--calendar-muted); background: rgba(255, 252, 245, 0.7); font-family: 'Manrope', sans-serif; font-size: 9px; }
.guidance-good .guidance-card-head span::before { content: '＋'; margin-right: 4px; color: var(--calendar-green); }
.guidance-bad .guidance-card-head span::before { content: '—'; margin-right: 4px; color: var(--calendar-red); }
.guidance-card ul { display: grid; gap: 6px; margin-top: 9px; }
.guidance-card li { position: relative; padding-left: 11px; color: var(--calendar-muted); font-size: 10px; line-height: 1.55; }
.guidance-card li::before { content: '·'; position: absolute; left: 1px; color: var(--cinnabar); font-weight: 900; }
.guidance-card li.guidance-empty { padding-left: 0; color: rgba(128, 110, 95, 0.72); }
.guidance-card li.guidance-empty::before { display: none; }
.guidance-toggle { position: relative; z-index: 1; display: block; width: 100%; margin-top: 8px; color: var(--cinnabar-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 10px; font-weight: 900; text-align: center; }
.guidance-toggle span { margin-left: 3px; font-size: 13px; }

.actual-records { position: relative; z-index: 1; margin-top: 24px; padding-top: 19px; border-top: 1px solid rgba(184, 92, 80, 0.18); }
.actual-records-head { display: flex; align-items: end; justify-content: space-between; gap: 10px; }
.actual-records-head > div { display: grid; gap: 6px; }
.actual-records-head h4 { color: var(--calendar-ink); font-size: 18px; }
.actual-count { display: inline-flex; min-height: 23px; align-items: center; border: 1px solid rgba(184, 92, 80, 0.2); border-radius: 999px; padding: 0 9px; color: var(--cinnabar-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 10px; font-weight: 900; }
.actual-records-intro { margin-top: 9px; color: var(--calendar-muted); font-size: 11px; line-height: 1.65; }
.actual-record-list { display: grid; gap: 8px; margin-top: 13px; }
.actual-record-item { padding: 11px 12px; border: 1px solid rgba(139, 90, 20, 0.12); border-radius: 12px; background: rgba(255, 252, 245, 0.58); }
.actual-record-meta { display: flex; align-items: center; gap: 6px; }
.record-kind, .record-status { display: inline-flex; min-height: 19px; align-items: center; border-radius: 999px; padding: 0 7px; font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 9px; font-weight: 900; }
.record-kind { color: var(--cinnabar-deep); background: rgba(184, 92, 80, 0.1); }
.record-kind.kind-decision { color: var(--gold-deep); background: rgba(217, 186, 98, 0.18); }
.record-status { color: #4f806f; background: rgba(111, 159, 147, 0.13); }
.record-status.status-doing { color: var(--gold-deep); background: rgba(217, 186, 98, 0.18); }
.record-status.status-skipped { color: var(--calendar-red); background: rgba(180, 93, 88, 0.1); }
.record-delete { margin-left: auto; color: var(--calendar-muted); font-size: 10px; opacity: 0; transition: color 0.2s ease, opacity 0.2s ease; }
.actual-record-item:hover .record-delete, .record-delete:focus-visible { opacity: 1; }
.record-delete:hover { color: var(--cinnabar-deep); }
.actual-record-item > p { margin-top: 8px; color: var(--calendar-ink); font-size: 12px; line-height: 1.6; }
.actual-record-item > small { display: block; margin-top: 4px; color: var(--calendar-muted); font-size: 10px; line-height: 1.55; }
.actual-record-empty { margin-top: 13px; padding: 12px; border: 1px dashed rgba(139, 90, 20, 0.17); border-radius: 12px; color: var(--calendar-muted); font-size: 11px; line-height: 1.65; }
.quick-records { display: grid; gap: 7px; margin-top: 15px; }
.quick-records-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; color: var(--calendar-ink); font-size: 11px; font-weight: 900; }
.quick-records-head small { color: var(--calendar-muted); font-size: 9px; font-weight: 500; }
.quick-record-button { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; padding: 8px 10px; border: 1px solid rgba(111, 159, 147, 0.18); border-radius: 10px; background: rgba(111, 159, 147, 0.07); color: var(--calendar-muted); font-size: 11px; line-height: 1.4; text-align: left; transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease; }
.quick-record-button:hover:not(:disabled) { transform: translateX(2px); border-color: rgba(111, 159, 147, 0.42); background: rgba(111, 159, 147, 0.13); }
.quick-record-button b { flex: 0 0 auto; color: #4f806f; font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 9px; font-weight: 900; white-space: nowrap; }
.quick-record-button.recorded { border-color: rgba(111, 159, 147, 0.3); background: rgba(111, 159, 147, 0.12); }
.quick-record-button:disabled { cursor: default; opacity: 0.82; }
.record-add-button { display: flex; align-items: center; justify-content: center; width: 100%; min-height: 41px; margin-top: 13px; border: 1px dashed rgba(184, 92, 80, 0.36); border-radius: 11px; background: rgba(184, 92, 80, 0.055); color: var(--cinnabar-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 11px; font-weight: 900; transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease; }
.record-add-button span { margin-right: 5px; font-size: 16px; font-weight: 500; }
.record-add-button:hover { transform: translateY(-1px); border-color: rgba(184, 92, 80, 0.58); background: rgba(184, 92, 80, 0.1); }
.record-form { display: grid; gap: 11px; margin-top: 13px; padding: 14px; border: 1px solid rgba(184, 92, 80, 0.2); border-radius: 13px; background: rgba(255, 250, 240, 0.66); }
.record-form-head { display: flex; align-items: center; justify-content: space-between; color: var(--calendar-ink); font-size: 12px; font-weight: 900; }
.record-form-head button { color: var(--calendar-muted); font-size: 10px; }
.record-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.record-form label { display: grid; gap: 5px; min-width: 0; }
.record-form label > span { color: var(--calendar-muted); font-size: 10px; }
.record-form select, .record-form input, .record-form textarea { width: 100%; border: 1px solid rgba(139, 90, 20, 0.14); border-radius: 9px; padding: 8px 9px; background: rgba(255, 252, 245, 0.8); color: var(--calendar-ink); font-size: 11px; }
.record-form textarea { resize: vertical; line-height: 1.6; }
.record-form select:focus, .record-form input:focus, .record-form textarea:focus { border-color: rgba(184, 92, 80, 0.5); outline: 0; box-shadow: 0 0 0 3px rgba(184, 92, 80, 0.1); }
.record-form-actions { display: flex; justify-content: end; gap: 7px; }
.record-form-actions .primary-button, .record-form-actions .secondary-button { min-height: 36px; padding: 0 13px; font-size: 10px; }
.record-form-actions .primary-button:disabled { cursor: wait; opacity: 0.65; }
.record-error { color: var(--cinnabar-deep); font-size: 10px; line-height: 1.5; }
.record-feedback { margin-top: 9px; color: #4f806f; font-size: 10px; line-height: 1.5; }
.record-storage-note { display: flex; align-items: center; gap: 5px; margin-top: 13px; color: var(--calendar-muted); font-size: 9px; }
.record-storage-note i { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: var(--calendar-green); }
.detail-reset { position: relative; z-index: 1; margin-top: 15px; }

.phase-rail { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
.phase-card { display: flex; min-width: 0; align-items: center; gap: 10px; border: 1px solid rgba(139, 90, 20, 0.13); border-radius: 15px; padding: 13px; background: rgba(255, 252, 245, 0.5); text-align: left; transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease; }
.phase-card:hover, .phase-card.active { transform: translateY(-2px); border-color: rgba(184, 92, 80, 0.33); background: rgba(255, 252, 245, 0.9); }
.phase-card-index { color: var(--cinnabar); font-family: 'Manrope', sans-serif; font-size: 10px; font-weight: 900; }
.phase-card-copy { display: grid; min-width: 0; gap: 4px; }
.phase-card-copy strong { overflow: hidden; color: var(--calendar-ink); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.phase-card-copy small { color: var(--calendar-muted); font-size: 10px; }
.phase-card-arrow { margin-left: auto; color: var(--cinnabar-deep); font-size: 16px; }

.compact-heading { align-items: end; }

.decision-table { overflow: hidden; }
.decision-row { display: grid; grid-template-columns: 0.7fr 0.55fr 0.45fr 2fr; align-items: center; width: 100%; gap: 12px; border-bottom: 1px solid rgba(139, 90, 20, 0.1); padding: 16px 21px; color: var(--calendar-muted); font-size: 13px; text-align: left; }
.decision-row:last-child { border-bottom: 0; }
.decision-row:not(.decision-head) { transition: background 0.2s ease; }
.decision-row:not(.decision-head):hover { background: rgba(184, 92, 80, 0.06); }
.decision-head { color: var(--gold-deep); font-family: 'Manrope', 'PingFang SC', sans-serif; font-size: 10px; font-weight: 900; letter-spacing: 0.13em; text-transform: uppercase; }
.decision-row strong { color: var(--calendar-ink); }
.node-pillar { color: var(--cinnabar-deep); font-weight: 900; letter-spacing: 0.08em; }
.node-type { color: var(--calendar-ink); }
.node-type b { float: right; color: var(--cinnabar); font-size: 16px; font-weight: 500; }

.record-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 15px; }
.record-card { position: relative; min-height: 184px; padding: 23px; overflow: hidden; }
.record-card::after { content: ''; position: absolute; right: -24px; bottom: -42px; width: 105px; aspect-ratio: 1; border: 1px solid rgba(184, 92, 80, 0.12); border-radius: 50%; box-shadow: 0 0 0 16px rgba(184, 92, 80, 0.05), 0 0 0 32px rgba(184, 92, 80, 0.04); }
.record-index { color: var(--cinnabar); font-family: 'Manrope', sans-serif; font-size: 11px; font-weight: 900; letter-spacing: 0.14em; }
.record-card h3 { margin-top: 17px; color: var(--calendar-ink); font-size: 21px; }
.record-card p { max-width: 250px; margin-top: 10px; color: var(--calendar-muted); font-size: 13px; line-height: 1.7; }
.record-line { position: absolute; left: 23px; bottom: 22px; width: 45px; height: 2px; background: var(--cinnabar); }

.caution-strip { display: flex; align-items: center; gap: 16px; margin-top: 17px; padding: 17px 21px; background: rgba(184, 92, 80, 0.08); }
.caution-seal { display: grid; flex: 0 0 46px; place-items: center; width: 46px; aspect-ratio: 1; border: 1px solid rgba(184, 92, 80, 0.48); border-radius: 50%; color: var(--cinnabar-deep); font-size: 10px; font-weight: 900; line-height: 1.2; text-align: center; transform: rotate(-7deg); }
.caution-strip strong { color: var(--cinnabar-deep); font-size: 14px; }
.caution-strip p { margin-top: 3px; color: var(--calendar-muted); font-size: 12px; }
.caution-mark { margin-left: auto; color: rgba(158, 63, 53, 0.35); font-size: 22px; font-weight: 900; letter-spacing: 0.1em; }

.detail-scrim { display: none; }

@media (max-width: 1000px) {
  .calendar-hero-inner { grid-template-columns: minmax(0, 1fr) minmax(280px, 0.74fr); gap: 28px; }
  .calendar-hero h1 { font-size: clamp(41px, 6vw, 64px); }
  .calendar-layout { grid-template-columns: minmax(0, 1fr) minmax(290px, 0.7fr); }
  .date-cell, .calendar-empty { min-height: 100px; }
  .date-cell-status { font-size: 8px; }
  .phase-card { padding: 11px 9px; }
}

@media (max-width: 900px) {
  .calendar-hero-inner { grid-template-columns: 1fr; min-height: auto; padding-top: 58px; }
  .calendar-hero-copy { max-width: 720px; }
  .orbit-card { justify-self: start; width: min(100%, 390px); }
  .overview-grid { grid-template-columns: 1fr; }
  .calendar-layout { display: block; }
  .day-detail { position: fixed; z-index: 1300; left: 12px; right: 12px; bottom: 12px; top: auto; max-height: calc(100svh - 24px); overflow-y: auto; opacity: 0; visibility: hidden; transform: translateY(calc(100% + 30px)); transition: opacity 0.28s ease, visibility 0.28s ease, transform 0.28s ease; }
  .day-detail.is-open { opacity: 1; visibility: visible; transform: translateY(0); }
  .detail-close { position: absolute; z-index: 2; top: 12px; right: 15px; display: block; width: 30px; height: 30px; border: 1px solid rgba(139, 90, 20, 0.14); border-radius: 50%; color: var(--calendar-muted); font-size: 24px; line-height: 26px; }
  .detail-scrim { position: fixed; z-index: 1250; inset: 0; display: block; background: rgba(47, 36, 27, 0.28); backdrop-filter: blur(3px); }
  .mobile-detail-launch { display: block; }
  .record-delete { opacity: 1; }
  .phase-rail { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
  .calendar-hero { min-height: auto; }
  .calendar-hero-inner { width: min(100% - 28px, 640px); padding-top: 42px; padding-bottom: 46px; }
  .calendar-hero h1 { font-size: clamp(37px, 11vw, 55px); }
  .calendar-hero-intro { font-size: 16px; line-height: 1.75; }
  .calendar-hero-meta { gap: 6px; margin-top: 23px; }
  .hero-chip { font-size: 10px; }
  .orbit-card { width: 100%; padding: 20px; }
  .orbit-ring-outer { width: 230px; }
  .calendar-section-heading { display: grid; gap: 15px; margin-bottom: 22px; }
  .calendar-section-heading .section-desc { text-align: left; }
  .calendar-heading-side { justify-items: start; gap: 9px; }
  .calendar-trace-summary { font-size: 11px; }
  .legend { justify-content: start; }
  .month-board { padding: 13px; }
  .month-board-head { margin-bottom: 18px; }
  .month-board-head h3 { font-size: 24px; }
  .today-button { padding: 8px 10px; font-size: 10px; }
  .calendar-weekdays, .calendar-grid { gap: 4px; }
  .calendar-weekdays span { font-size: 9px; letter-spacing: 0.08em; }
  .calendar-empty { min-height: 74px; border-radius: 10px; }
  .date-cell { min-height: 74px; border-radius: 10px; padding: 7px 6px; }
  .date-cell::after { right: -14px; top: -14px; width: 38px; }
  .date-cell-top strong { font-size: 18px; }
  .date-cell-top em { display: none; }
  .date-cell-pillar { margin-top: 5px; font-size: 9px; letter-spacing: 0.04em; }
  .date-cell-keyword { font-size: 10px; }
  .date-cell-status { display: none; }
  .today-mark { right: 5px; bottom: 5px; font-size: 7px; }
  .date-cell-record { font-size: 7px; }
  .phase-rail { gap: 7px; }
  .phase-card { gap: 6px; padding: 10px 8px; }
  .phase-card-index { font-size: 9px; }
  .phase-card-copy strong { font-size: 10px; }
  .phase-card-copy small { font-size: 9px; }
  .phase-card-arrow { font-size: 13px; }
  .decision-row { grid-template-columns: 0.68fr 0.55fr 0.38fr 1.6fr; gap: 7px; padding: 14px 12px; font-size: 11px; }
  .decision-head { font-size: 8px; }
  .node-type b { display: none; }
  .record-grid { grid-template-columns: 1fr; }
  .record-card { min-height: 150px; }
  .caution-strip { align-items: start; padding: 15px; }
  .caution-strip strong { font-size: 13px; }
  .caution-strip p { line-height: 1.5; }
  .caution-mark { display: none; }
  .day-detail { left: 8px; right: 8px; bottom: 8px; padding: 21px 18px; }
  .detail-header h3 { font-size: 26px; }
  .keyword-stamp { flex-basis: 58px; width: 58px; }
  .keyword-stamp strong { font-size: 17px; }
  .actual-records-head h4 { font-size: 16px; }
  .quick-records-head { align-items: start; flex-direction: column; gap: 3px; }
  .record-form-grid { grid-template-columns: 1fr; }
}
</style>
