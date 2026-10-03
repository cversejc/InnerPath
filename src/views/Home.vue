<template>
  <div class="page-shell home">
    <BrandNav />

    <section class="landscape-hero hero">
      <div class="container hero-layout">
        <div class="hero-copy">
          <p class="section-kicker">Life Timeline / CHENVIS</p>
          <h1>辰鉴</h1>
          <p class="hero-intro">
            把你的个人特质、当下节奏和现实选择放在一张地图上，帮你更清楚地走下一步
          </p>
        </div>
      </div>
    </section>

    <section class="section-band intro-section">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">FOR THE STUCK MOMENT</p>
          <h2 class="section-title">不是安慰你，而是帮你看清自己为何停在这里</h2>
        </div>
        <div class="paper-card prose-card">
          <p>你不一定缺少努力，也不一定需要再听一句“你应该怎样”，很多时候，卡住是因为个人属性、环境时序和行动方式没有对上</p>
          <p>辰鉴不替你评判人生，也不替你决定未来，先看见“我是谁”，再在自己的节奏里找到更适合的用力方式</p>
          <p class="emphasis">社会属性可以被重新理解，个人属性值得被认真肯定</p>
        </div>
      </div>
    </section>

    <section class="section-band alt">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">HOW IT HELPS</p>
          <h2 class="section-title">一本说明书，多种视角</h2>
          <p class="section-desc">
            八字、紫微、星盘等传统工具提供观察角度，读懂你的特质与处境；心理学和哲学帮助你把看见的内容变成生活中每天可以使用的行动提示。
          </p>
        </div>
        <div class="method-grid">
          <article class="paper-card method-card">
            <span>FI / 01</span>
            <h3>我是谁</h3>
            <p>性格密码、天赋与暗面天赋、能量通路，以及你与关系的互动模式</p>
          </article>
          <article class="paper-card method-card">
            <span>FI / 02</span>
            <h3>我卡在哪</h3>
            <p>看见当下核心矛盾、人生重复模式，以及潜意识正在保护什么</p>
          </article>
          <article class="paper-card method-card">
            <span>TE / 03</span>
            <h3>我往哪去</h3>
            <p>从下周可做的三件事，到未来 6—12 个月的能力建设和决策日历</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band services-preview">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">YOUR PATH</p>
          <h2 class="section-title">从看见自己，到做出更适合的选择</h2>
          <p class="section-desc">一份个人报告书，帮你理解自己的特质与处境；一张决策日历，帮你把重要选择放在适合的时机</p>
        </div>
        <div class="services-grid launch-tools-grid">
          <article class="paper-card service-card">
            <span class="seal-badge">01 / PERSONAL REPORT</span>
            <h3>个人报告书</h3>
            <p class="tool-lead">先把“我是谁、我卡在哪”写清楚</p>
            <ul class="service-features">
              <li>个人属性、天赋与能量通路</li>
              <li>核心矛盾与人生重复模式</li>
              <li>当前阶段的环境坐标</li>
            </ul>
            <VanButton class="secondary-button" native-type="button" @click="goToAssessment"><IconMark name="reports" />申请我的说明书</VanButton>
          </article>
          <article class="paper-card service-card featured launch-calendar-card">
            <span class="seal-badge">02 / DECISION CALENDAR</span>
            <h3>决策日历</h3>
            <p class="tool-lead">把“知道自己”变成每天可使用的节奏</p>
            <ul class="service-features">
              <li>查看当下阶段的行动气候</li>
              <li>按日期获得适合与暂缓事项</li>
              <li>留下真实行动记录，持续复盘</li>
            </ul>
            <VanButton class="primary-button" type="primary" native-type="button" @click="goToCalendar"><IconMark name="calendar" />打开我的日历</VanButton>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band final-cta">
      <div class="container final-cta-inner">
        <p class="section-kicker">NEXT STEP</p>
        <h2>先写一页属于你的说明书</h2>
        <p>不算命，不评判，不替你预言未来，先从“我是谁”开始</p>
        <VanButton class="primary-button" type="primary" native-type="button" @click="goToAssessment"><IconMark name="compass" />开始探索</VanButton>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'

export default {
  name: 'Home',
  components: { VanButton },
  methods: {
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    }
  }
}
</script>

<style scoped src="./Home.css"></style>
<style scoped src="./Home-responsive.css"></style>
