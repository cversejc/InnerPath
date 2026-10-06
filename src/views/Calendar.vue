<template>
  <div class="page-shell calendar-page">
    <BrandNav />

    <BrandPageHeader v-if="loading || !calendar || !days.length" eyebrow="YOUR PERSONAL TIMING" title="给行动，找到自己的节奏" description="一段三十天的个人日历。看见适合推进与停留的时刻，把每一次选择留成可回看的记录。" seal="知序" />

    <main v-if="loading" class="calendar-empty-state">
      <div class="container calendar-loading" role="status" aria-live="polite"><IconMark name="calendar" /><h2>正在为你打开决策日历…</h2></div>
    </main>

    <main v-else-if="!calendar || !days.length" class="calendar-empty-state">
      <div class="container paper-card">
        <span class="calendar-empty-seal" aria-hidden="true"><IconMark name="calendar" /></span>
        <p class="section-kicker">A NEW RHYTHM</p>
        <h2>为接下来的三十天，留一点从容</h2>
        <p>{{ calendarError || (reports.length ? '选择一份已交付报告，补充这 30 天的目标。生成成功后，日历会自动开放使用。' : '请先申请报告并等待咨询师交付。获得报告后，回到这里即可生成决策日历。') }}</p>
        <div class="calendar-empty-actions">
          <router-link class="primary-button" :to="reports.length ? '/pages/calendar/calendar?generate=1' : '/pages/assessment/assessment'">{{ reports.length ? '基于报告生成日历' : '先申请报告' }}</router-link>
          <router-link class="secondary-button" to="/pages/requests/requests">查看我的申请</router-link>
        </div>
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
              <span v-if="calendarSource === 'mock'" class="hero-chip hero-chip-demo">参考节奏</span>
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
            <p class="section-desc">这张日历不是催你每天做更多，而是帮你分辨什么时候适合推进，什么时候适合停下来整理。</p>
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
                  <li><span>01</span>把眼下最重要的事情写下来，找到清晰的下一步。</li>
                  <li><span>02</span>记录 3—5 次真实选择，回看自己如何做决定。</li>
                  <li><span>03</span>给重要的人和事情留出沟通与等待的时间。</li>
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

      <CalendarPlanningSection
        ref="planningSection"
        :action-climate="actionClimate"
        :calendar-cells="calendarCells"
        :calendar-label="calendarLabel"
        :hidden-guidance-count="hiddenGuidanceCount"
        :is-mobile-layout="isMobileLayout"
        :meta="meta"
        :month-record-count="monthRecordCount"
        :month-record-days="monthRecordDays"
        :mobile-detail-open="mobileDetailOpen"
        :phases="phases"
        :record-draft="recordDraft"
        :record-error="recordError"
        :record-feedback="recordFeedback"
        :record-source="recordSource"
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
        :weekdays="weekdays"
        @close-mobile-detail="closeMobileDetail"
        @detail-keydown="handleDetailKeydown"
        @close-record-form="closeRecordForm"
        @open-mobile-detail="openMobileDetail"
        @open-record-form="openRecordForm"
        @quick-record="quickRecord"
        @remove-record="removeDecisionLog"
        @save-record="saveDecisionLog"
        @select-date="selectDate"
        @show-current-date="showCurrentDate"
        @toggle-guidance="showFullGuidance = !showFullGuidance"
        @update-record-draft="updateRecordDraft"
      />

      <section class="section-band decision-section">
        <div class="container">
          <div class="calendar-section-heading compact-heading">
            <div><p class="section-kicker">DECISION WINDOWS</p><h2 class="section-title">本月关键决策节点</h2></div>
            <p class="section-desc">不是每一天都需要完成大事。把重要动作交给真正支持它的窗口。</p>
          </div>
          <div class="decision-table paper-card">
            <div class="decision-row decision-head"><span>日期</span><span>日柱</span><span>色块</span><span>适合决策类型</span></div>
            <button v-for="node in decisionNodes" :key="node.date" type="button" class="decision-row" :aria-pressed="selectedDate === node.dateKey" @click="selectDecisionNode(node)">
              <span><strong>{{ node.date }}</strong></span>
              <span class="node-pillar">{{ node.pillar }}</span>
              <span><i class="legend-dot" :class="`legend-dot-${node.tone}`"></i></span>
              <span class="node-type">{{ node.type }} <IconMark name="arrow" /></span>
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

    <CalendarRequestSection
      v-if="!loading && (reports.length || calendar)"
      :calendar-requests="calendarRequests"
      :reports="reports"
      :show-form="showCalendarRequestForm"
      :draft="calendarRequestDraft"
      :profile="profile"
      :submitting="submittingCalendarRequest"
      :error="calendarRequestError"
      :feedback="calendarRequestFeedback"
      :topic-options="calendarTopicOptions"
      :usage-options="calendarUsageOptions"
      :outcome-options="calendarOutcomeOptions"
      @open="openCalendarRequest"
      @close="closeCalendarRequest"
      @go-to-profile="goToProfile"
      @submit="submitCalendarRequest"
      @toggle-topic="toggleCalendarTopic"
      @toggle-outcome="toggleCalendarOutcome"
    />

    <BrandFooter />

    <div v-if="mobileDetailOpen" class="detail-scrim" @click="closeMobileDetail"></div>
  </div>
</template>

<script src="./Calendar.js"></script>

<style src="./Calendar.css"></style>
