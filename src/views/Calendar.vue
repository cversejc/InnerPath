<template>
  <div class="page-shell calendar-page">
    <BrandNav />

    <main>
      <section class="calendar-hero">
        <div class="container calendar-hero-inner">
          <div class="calendar-hero-copy">
            <p class="section-kicker">TE / DECISION TIMING</p>
            <p class="calendar-overline">{{ meta.subtitle }}</p>
            <h1>辰鉴 <span>·</span> 你的丁酉月<br /><em>时区说明书</em></h1>
            <p class="calendar-hero-intro">{{ meta.intro }} 用舍由时，行藏在我：顺着环境做选择，在有助推力的时候冲锋，在风浪大的时候稳住修整。</p>
            <div class="calendar-hero-meta">
              <span class="hero-chip hero-chip-date">{{ meta.dateLabel }}</span>
              <span class="hero-chip">{{ meta.pillars }}</span>
              <span class="hero-chip hero-chip-rhythm">{{ meta.rhythm }}</span>
            </div>
          </div>

          <div class="orbit-card" aria-label="丁酉月节奏图示">
            <div class="orbit-ring orbit-ring-outer">
              <span class="orbit-glyph orbit-glyph-top">观</span>
              <span class="orbit-glyph orbit-glyph-right">行</span>
              <span class="orbit-glyph orbit-glyph-bottom">息</span>
              <span class="orbit-glyph orbit-glyph-left">记</span>
              <div class="orbit-ring orbit-ring-inner">
                <div class="orbit-core"><span>丁</span><strong>酉</strong></div>
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
            <p class="section-desc">丁酉月像一张低声运转的后台地图：表面动作不多，判断、整合与等待都在发生。</p>
          </div>

          <div class="overview-grid">
            <article class="paper-card overview-story">
              <div class="card-ornament">「 丁酉月 · 总览 」</div>
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
              <h2 class="section-title">把每一天，放回它适合的位置</h2>
            </div>
            <div class="legend" aria-label="时区颜色图例">
              <span><i class="legend-dot legend-dot-green"></i>推进</span>
              <span><i class="legend-dot legend-dot-yellow"></i>准备</span>
              <span><i class="legend-dot legend-dot-red"></i>休整</span>
            </div>
          </div>

          <div class="calendar-layout">
            <section class="paper-card month-board" aria-label="2026年丁酉月日历">
              <header class="month-board-head">
                <div>
                  <span class="month-eyebrow">PERSONAL TIMEZONE</span>
                  <h3>2026 / 09—10</h3>
                  <p>甲申日 · 丁酉月末</p>
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
                    :aria-label="`${cell.month}月${cell.day}日，${cell.statusLabel}`"
                    :aria-selected="selectedDate === cell.date"
                    @click="selectDate(cell.date)"
                  >
                    <span class="date-cell-top"><strong>{{ String(cell.day).padStart(2, '0') }}</strong><em v-if="cell.month === 10">十月</em></span>
                    <span class="date-cell-pillar">{{ cell.dayPillar || cell.shortLabel }}</span>
                    <span class="date-cell-keyword">{{ cell.keyword || cell.shortLabel }}</span>
                    <span class="date-cell-status">{{ cell.statusLabel }}</span>
                    <span v-if="cell.isCurrentDay" class="today-mark">今天</span>
                  </button>
                </template>
              </div>

              <button v-if="!mobileDetailOpen" class="mobile-detail-launch" type="button" @click="mobileDetailOpen = true">
                查看 {{ selectedDay.month }}月{{ selectedDay.day }}日的时区导航 <span>↗</span>
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
              <div class="detail-keyword"><span>今日关键词</span><strong>{{ selectedEntry.keyword }}</strong></div>
              <p class="detail-summary">{{ selectedEntry.isPhase ? selectedEntry.summary : `这一日适合把“${selectedEntry.keyword}”放在第一位。` }}</p>

              <div class="detail-columns">
                <div class="detail-list detail-list-good">
                  <span class="detail-list-label">适合做</span>
                  <ul><li v-for="item in selectedEntry.suitable" :key="item">{{ item }}</li></ul>
                </div>
                <div class="detail-list detail-list-bad">
                  <span class="detail-list-label">先不要做</span>
                  <ul><li v-for="item in selectedEntry.unsuitable" :key="item">{{ item }}</li></ul>
                </div>
              </div>

              <div class="time-window">
                <span class="time-window-icon">⌁</span>
                <div><span>换气口提醒</span><p>{{ selectedEntry.timeWindow }}</p></div>
              </div>

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
            <p class="section-desc">不求每天都高效，只记录那些让你更了解自己的时刻。</p>
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
import {
  calendarMeta,
  cautionNotes,
  createCalendarDays,
  decisionNodes,
  getDateEntry,
  isToday,
  phaseDefinitions,
  recordPrompts,
  resolveDefaultDate
} from '../data/decisionCalendar'

export default {
  name: 'Calendar',
  data() {
    const days = createCalendarDays()
    const defaultDate = resolveDefaultDate()

    return {
      meta: calendarMeta,
      phases: phaseDefinitions,
      days,
      weekdays: ['一', '二', '三', '四', '五', '六', '日'],
      selectedDate: defaultDate,
      todayDate: defaultDate,
      mobileDetailOpen: !(typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches),
      decisionNodes,
      recordPrompts,
      cautionNotes
    }
  },
  computed: {
    selectedDay() {
      return this.days.find(day => day.date === this.selectedDate) || this.days[0]
    },
    selectedEntry() {
      return getDateEntry(this.selectedDate) || {}
    },
    calendarCells() {
      const leading = (new Date(2026, 8, 7).getDay() + 6) % 7
      const trailing = (7 - ((leading + this.days.length) % 7)) % 7
      const emptyCells = Array.from({ length: leading + trailing }, (_, index) => ({
        key: `empty-${index}`,
        empty: true
      }))

      return [
        ...emptyCells.slice(0, leading),
        ...this.days.map(day => ({ ...day, key: day.date, isCurrentDay: isToday(day.date) })),
        ...emptyCells.slice(leading)
      ]
    }
  },
  mounted() {
    window.addEventListener('keydown', this.handleEscape)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleEscape)
  },
  methods: {
    selectDate(date) {
      this.selectedDate = date
      if (window.matchMedia('(max-width: 900px)').matches) {
        this.mobileDetailOpen = true
      }
    },
    selectDecisionNode(node) {
      const [, month, day] = node.date.match(/(\d+)月(\d+)日/) || []
      const dateKey = `2026-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
      this.selectDate(dateKey)
    },
    showCurrentDate() {
      this.selectedDate = this.todayDate
      this.mobileDetailOpen = true
    },
    handleEscape(event) {
      if (event.key === 'Escape') {
        this.mobileDetailOpen = false
      }
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

.legend { display: flex; flex-wrap: wrap; justify-content: end; gap: 13px; color: var(--calendar-muted); font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--calendar-muted); }
.legend-dot-green { background: var(--calendar-green); }
.legend-dot-yellow { background: var(--calendar-yellow); }
.legend-dot-red { background: var(--calendar-red); }
.legend-dot-yellow-green { background: linear-gradient(90deg, var(--calendar-yellow), var(--calendar-green)); }

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

.detail-keyword { display: flex; align-items: end; gap: 11px; margin-top: 21px; }
.detail-keyword span { color: var(--calendar-muted); font-size: 11px; }
.detail-keyword strong { color: var(--calendar-ink); font-size: 35px; line-height: 0.95; }
.detail-summary { position: relative; z-index: 1; margin-top: 16px; color: var(--calendar-muted); font-size: 14px; line-height: 1.8; }

.detail-columns { position: relative; z-index: 1; display: grid; gap: 15px; margin-top: 23px; }
.detail-list { padding-top: 13px; border-top: 1px solid rgba(139, 90, 20, 0.14); }
.detail-list-label { display: inline-block; color: var(--calendar-ink); font-size: 12px; font-weight: 900; }
.detail-list-good .detail-list-label::before { content: '＋'; margin-right: 5px; color: var(--calendar-green); }
.detail-list-bad .detail-list-label::before { content: '—'; margin-right: 5px; color: var(--calendar-red); }
.detail-list ul { display: grid; gap: 7px; margin-top: 9px; }
.detail-list li { position: relative; padding-left: 13px; color: var(--calendar-muted); font-size: 12px; line-height: 1.6; }
.detail-list li::before { content: '·'; position: absolute; left: 1px; color: var(--cinnabar); font-weight: 900; }

.time-window { position: relative; z-index: 1; display: grid; grid-template-columns: 27px 1fr; gap: 8px; margin-top: 20px; padding: 13px 14px; border: 1px solid rgba(111, 159, 147, 0.24); border-radius: 13px; background: rgba(111, 159, 147, 0.1); }
.time-window-icon { color: #4f806f; font-size: 22px; line-height: 1; }
.time-window span:not(.time-window-icon) { color: #4f806f; font-size: 10px; font-weight: 900; letter-spacing: 0.12em; }
.time-window p { margin-top: 5px; color: #5b7065; font-size: 11px; line-height: 1.65; }
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
  .detail-keyword strong { font-size: 31px; }
}
</style>
