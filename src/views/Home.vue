<template>
  <div class="page-shell home">
    <BrandNav />

    <main class="home-content">
      <section class="home-hero" aria-labelledby="home-hero-title">
        <div class="container home-hero-inner">
          <div class="home-hero-copy">
            <p class="section-kicker">CHENVIS</p>
            <h1 id="home-hero-title">看见自己，<br />找到自己的<span>节奏</span></h1>
            <p class="home-hero-description">
              把你的个人特质、当下节奏和现实选择，<br class="desktop-break" />
              放在一张清晰的人生地图里。
            </p>
            <div class="home-hero-actions">
              <VanButton class="primary-button" type="primary" native-type="button" @click="goToAssessment">
                <template #icon><IconMark name="compass" /></template>
                开始探索自己
              </VanButton>
              <router-link class="home-text-link" to="/pages/calendar/calendar">看看决策日历 <span aria-hidden="true">↗</span></router-link>
            </div>
          </div>
          <ul class="home-hero-features" aria-label="辰鉴探索方向">
            <li v-for="feature in heroFeatures" :key="feature.title" class="home-hero-feature">
              <span class="home-hero-feature-icon"><IconMark :name="feature.icon" /></span>
              <span class="home-hero-feature-copy">
                <strong>{{ feature.title }}</strong>
                <small>{{ feature.detail }}</small>
              </span>
            </li>
          </ul>
          <p class="home-hero-marker" aria-hidden="true"><span>过去</span><span>当下</span><span>未来</span></p>
        </div>
      </section>

      <section class="home-intro section-band" aria-labelledby="home-intro-title">
        <div class="container home-intro-inner">
          <p class="section-kicker">FOR THE STUCK MOMENT</p>
          <h2 id="home-intro-title">不是安慰你，而是帮你看清自己为何停在这里</h2>
          <span class="home-section-rule" aria-hidden="true"></span>
          <p>
            你不一定缺少努力。很多时候，卡住是因为个人属性、环境时序和行动方式没有对上。<br class="desktop-break" />
            辰鉴不替你评判人生，也不替你决定未来；先看见“我是谁”，再找到更适合自己的用力方式。
          </p>
          <p class="home-intro-emphasis">社会属性可以被重新理解，个人属性值得被认真肯定。</p>
        </div>
      </section>

      <section class="home-perspectives section-band" aria-labelledby="perspectives-title">
        <div class="container">
          <header class="home-perspectives-heading">
            <p class="section-kicker">HOW IT HELPS</p>
            <h2 id="perspectives-title">一本说明书，多种视角</h2>
            <span class="home-section-rule" aria-hidden="true"></span>
            <p>
              八字、紫微、星盘等传统工具提供观察角度；心理学和哲学帮助你把看见的内容，
              变成生活中可以使用的行动提示。
            </p>
          </header>
          <div class="perspective-grid">
            <article v-for="item in perspectives" :key="item.number" class="paper-card perspective-card">
              <div class="perspective-card-meta">
                <span class="perspective-number">{{ item.number }}</span>
                <span class="perspective-icon"><IconMark :name="item.icon" /></span>
              </div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description }}</p>
            </article>
          </div>
        </div>
      </section>

      <section class="path-section section-band" aria-labelledby="path-title">
        <div class="container">
          <header class="path-heading">
            <p class="section-kicker">YOUR PATH</p>
            <h2 id="path-title">从看见自己，到做出<span>更适合的选择</span></h2>
            <p>一本人生说明书，帮助你理解自己的特质与处境；一张决策日历，帮助你把重要选择放在适合的时机。</p>
          </header>

          <div class="path-grid">
            <article v-for="card in pathCards" :key="card.number" class="paper-card path-card">
              <div class="path-card-head">
                <div>
                  <p class="path-card-kicker"><span>{{ card.number }}</span><b>/</b>{{ card.eyebrow }}</p>
                  <h3>{{ card.title }}</h3>
                </div>
                <span class="path-card-icon"><IconMark :name="card.icon" /></span>
              </div>
              <p class="path-card-summary">{{ card.summary }}</p>
              <ul class="path-card-list">
                <li v-for="bullet in card.bullets" :key="bullet">{{ bullet }}</li>
              </ul>
              <router-link class="home-text-link path-card-link" :to="card.to">{{ card.action }} <span aria-hidden="true">↗</span></router-link>
            </article>
          </div>
        </div>
      </section>

      <section class="journey-section section-band" aria-labelledby="journey-title">
        <div class="container">
          <header class="journey-heading">
            <p class="section-kicker">HOW IT WORKS</p>
            <h2 id="journey-title">从了解自己，到用在生活里</h2>
          </header>

          <ol class="journey-steps" aria-label="自我探索的四个步骤">
            <li v-for="step in journeySteps" :key="step.number" class="journey-step">
              <div class="journey-step-head">
                <span class="journey-step-number">{{ step.number }}</span>
                <span class="journey-step-icon"><IconMark :name="step.icon" /></span>
              </div>
              <div class="journey-step-copy">
                <h3>{{ step.title }}</h3>
                <p>{{ step.description }}</p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      <section class="belief-section section-band" aria-labelledby="belief-title">
        <div class="container belief-inner">
          <p class="section-kicker">OUR BELIEF</p>
          <h2 id="belief-title">报告不是答案，而是<span>一面镜子</span></h2>
          <span class="home-section-rule" aria-hidden="true"></span>
          <p>传统工具提供观察角度，心理学与哲学帮助理解与行动。<br class="desktop-break" />每个判断都应回到你的真实经历，由你决定如何使用。</p>
        </div>
      </section>

      <section class="home-manifesto" aria-labelledby="start-title">
        <div class="container manifesto-inner">
          <div class="home-start" aria-labelledby="start-title">
            <p class="section-kicker">NEXT STEP</p>
            <h2 id="start-title">先写一本属于你的说明书</h2>
            <p>不算命，不评判，不替你预言未来，先从“我是谁”开始。</p>
            <div class="home-start-actions">
              <VanButton class="primary-button home-start-button" type="primary" native-type="button" @click="goToAssessment">
                <template #icon><IconMark name="compass" /></template>
                开始探索
              </VanButton>
            </div>
          </div>
        </div>
      </section>
    </main>

    <BrandFooter />
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'
import IconMark from '../components/IconMark.vue'

export default {
  name: 'Home',
  components: { VanButton, IconMark },
  data() {
    return {
      heroFeatures: [
        { icon: 'compass', title: '认识自己', detail: '个人特质' },
        { icon: 'refresh', title: '把握节奏', detail: '生活与选择' },
        { icon: 'spark', title: '找到方向', detail: '更适合的人生' }
      ],
      pathCards: [
        {
          number: '01',
          eyebrow: 'PERSONAL REPORT',
          icon: 'document',
          title: '人生说明书',
          to: '/pages/assessment/assessment',
          action: '写下我的说明书',
          summary: '先清楚我是谁，我卡在哪，往哪走。',
          bullets: ['个人属性、天赋与能量通路', '核心矛盾与人生重复模式', '当前阶段的环境坐标']
        },
        {
          number: '02',
          eyebrow: 'DECISION CALENDAR',
          icon: 'calendar',
          title: '决策日历',
          to: '/pages/calendar/calendar',
          action: '查看我的日历',
          summary: '把“了解自己”变成每天可使用的节奏。',
          bullets: ['行动建议', '适宜行动和需缓事项', '留下真实行动记录，持续复盘']
        }
      ],
      journeySteps: [
        { number: '01', icon: 'document', title: '回答问题', description: '基于生活、情绪、关系等多维度，诚实地回答问题。' },
        { number: '02', icon: 'reports', title: '生成个人说明书', description: '系统梳理你的特质、卡点与阶段环境。' },
        { number: '03', icon: 'growth', title: '查看当下节奏', description: '理解当前所处的阶段与环境，看见机会与挑战。' },
        { number: '04', icon: 'calendar', title: '使用决策日历', description: '在关键时刻做更适合的选择，并持续记录与复盘。' }
      ],
      perspectives: [
        { number: '01', icon: 'person', title: '我是谁', description: '看见性格特质、天赋与能量通路，以及你与关系的互动方式。' },
        { number: '02', icon: 'refresh', title: '我卡在哪', description: '看清当下的核心矛盾、反复出现的模式，以及旧循环正在保护什么。' },
        { number: '03', icon: 'compass', title: '我往哪去', description: '从眼前能做的小事，到未来能力建设与决策节奏，找到可尝试的方向。' }
      ]
    }
  },
  methods: {
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    }
  }
}
</script>

<style scoped src="./Home.css"></style>
<style scoped src="./Home-responsive.css"></style>
