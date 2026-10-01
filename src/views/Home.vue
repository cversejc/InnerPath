<template>
  <div class="page-shell home">
    <BrandNav />

    <section class="landscape-hero hero">
      <div class="container hero-layout">
        <div class="hero-copy">
          <p class="section-kicker">Life Timeline / CHEN JIAN</p>
          <h1>辰鉴</h1>
          <p class="hero-intro">
            把你的个人特质、当下节奏和现实选择放在一张地图上，帮你更清楚地走下一步
          </p>
          <div class="hero-actions">
            <button class="primary-button" type="button" @click="goToAssessment"><IconMark name="reports" />申请人生说明书</button>
            <button class="secondary-button" type="button" @click="goToCalendar"><IconMark name="calendar" />打开决策日历</button>
          </div>
        </div>
      </div>
    </section>

    <section v-if="profile" class="section-band profile-journey-section">
      <div class="container profile-journey-shell">
        <ProfileGrowthCard
          :profile="profile"
          :completion="profileCompletion"
          :last-confirmed-at="profile.profile_last_confirmed_at"
          @edit="goToProfile"
        />
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
          <h2 class="section-title">一张说明书，两个方向</h2>
          <p class="section-desc">
            先读懂你的特质与处境，再把洞察变成每天可以使用的行动提示，八字、紫微、星盘等传统工具提供观察角度，心理学和哲学帮助你把看见的内容用回生活
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
            <button class="secondary-button" type="button" @click="goToAssessment"><IconMark name="reports" />申请我的说明书</button>
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
            <button class="primary-button" type="button" @click="goToCalendar"><IconMark name="calendar" />打开我的日历</button>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band final-cta">
      <div class="container final-cta-inner">
        <p class="section-kicker">NEXT STEP</p>
        <h2>先写一页属于你的说明书</h2>
        <p>不算命，不评判，不替你预言未来，先从“我是谁”开始</p>
        <button class="primary-button" type="button" @click="goToAssessment"><IconMark name="compass" />开始探索</button>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { getCurrentUser } from '../utils/authService'
import ProfileGrowthCard from '../components/ProfileGrowthCard.vue'

export default {
  name: 'Home',
  components: { ProfileGrowthCard },
  data() {
    return {
      profile: null,
      profileCompletion: 0
    }
  },
  async mounted() {
    try {
      const user = await getCurrentUser()
      this.profile = user
      this.profileCompletion = Number(user.profile_completion || 0)
    } catch (error) {
      // 首页仍然可以浏览，档案卡片只在用户资料读取成功时出现，
      console.warn('读取首页个人档案失败', error)
    }
  },
  methods: {
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    },
    goToProfile() {
      this.$router.push('/pages/user/user?tab=settings')
    }
  }
}
</script>

<style scoped>
.hero {
  padding: clamp(56px, 9vw, 104px) 0 clamp(64px, 9vw, 100px);
}

.home .section-kicker {
  text-transform: none;
}

.hero-layout {
  display: block;
}

.hero-copy {
  width: min(100%, 760px);
  margin: 0 auto;
  text-align: center;
}

.hero h1 {
  color: var(--ink);
  font-size: clamp(58px, 12vw, 112px);
  font-weight: 900;
  line-height: 1.04;
  letter-spacing: 0.1em;
  text-indent: 0.1em;
}

.hero-intro {
  width: min(100%, 600px);
  margin: 16px auto 0;
  color: var(--ink-soft);
  font-size: 15px;
  line-height: 1.9;
}

.profile-journey-section {
  padding-top: 20px;
  padding-bottom: 20px;
}

.profile-journey-shell {
  width: min(900px, 100%);
}

.hero-actions {
  display: flex;
  width: 100%;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: clamp(30px, 5vw, 52px);
}

.hero-actions > * {
  min-width: 0;
}

.prose-card {
  width: min(100%, 720px);
  margin: 0 auto;
  padding: clamp(24px, 4vw, 38px);
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.9;
  text-align: center;
}

.prose-card p + p {
  margin-top: 16px;
}

.prose-card .emphasis {
  color: var(--cinnabar-deep);
  font-weight: 800;
}

.section-heading {
  max-width: 760px;
  margin: 0 auto 34px;
  text-align: center;
}

.method-grid,
.services-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.services-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  max-width: 860px;
  margin: 0 auto;
}

.method-card,
.service-card {
  padding: 26px;
}

.method-card {
  display: grid;
  justify-items: center;
  text-align: center;
}

.method-card span {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(184, 92, 80, 0.22);
  border-radius: 999px;
  padding: 0 14px;
  background: rgba(184, 92, 80, 0.08);
  color: var(--cinnabar-deep);
  font-family: var(--font-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.service-card .seal-badge {
  width: 100%;
  justify-content: center;
}

.method-card h3,
.service-card h3 {
  margin-top: 14px;
  color: var(--ink);
  font-size: 22px;
  line-height: 1.35;
}

.tool-lead {
  margin-top: 10px;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.7;
}

.method-card p {
  margin-top: 12px;
  color: var(--ink-soft);
  line-height: 1.75;
}

.service-card {
  display: flex;
  min-height: 420px;
  flex-direction: column;
}

.service-card.featured {
  border-color: rgba(184, 92, 80, 0.32);
  background:
    linear-gradient(180deg, rgba(255, 252, 245, 0.96), rgba(255, 239, 222, 0.82));
}

.price {
  margin: 16px 0 18px;
  color: var(--cinnabar-deep);
  font-family: var(--font-ui);
  font-size: 26px;
  font-weight: 900;
}

.service-features {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
  color: var(--ink-soft);
  line-height: 1.6;
}

.service-features li {
  position: relative;
  padding-left: 18px;
}

.service-features li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}

.service-card button {
  width: 100%;
  margin-top: auto;
}

.final-cta {
  text-align: center;
}

.final-cta-inner {
  border-top: 1px solid var(--line);
  padding-top: 44px;
}

.final-cta h2 {
  margin-bottom: 24px;
  font-size: clamp(28px, 6vw, 46px);
  line-height: 1.2;
}

@media (min-width: 1024px) {
  .hero {
    display: grid;
    min-height: 520px;
    align-items: center;
    padding: 64px 0 76px;
  }

  .hero-copy {
    width: min(100%, 880px);
  }

  .hero h1 {
    font-size: 104px;
  }

  .hero-intro {
    margin-top: 18px;
    font-size: 16px;
  }

  .hero-actions {
    margin-top: 48px;
  }
}

@media (max-width: 900px) {
  .method-grid,
  .services-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .hero {
    padding: 34px 0 42px;
  }

  .hero h1 {
    font-size: clamp(50px, 17vw, 72px);
    line-height: 1.1;
  }

  .hero-intro {
    margin-top: 12px;
    font-size: 14px;
    line-height: 1.8;
  }

  .hero-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-top: 40px;
  }

  .hero-actions > * {
    width: 100%;
  }

  .hero-actions .primary-button,
  .hero-actions .secondary-button {
    min-height: 46px;
    padding-right: 8px;
    padding-left: 8px;
    font-size: 13px;
  }

  .method-card,
  .service-card,
  .prose-card {
    padding: 16px;
    border-radius: 14px;
  }

  .service-card {
    min-height: 0;
  }

  .section-band {
    padding-top: 40px;
    padding-bottom: 40px;
  }

  .profile-journey-section {
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .section-heading {
    margin-bottom: 22px;
  }

  .method-grid,
  .services-grid {
    gap: 12px;
  }

  .method-card span {
    width: 64px;
    font-size: 11px;
  }

  .method-card h3,
  .service-card h3 {
    margin-top: 10px;
    font-size: 20px;
  }

  .tool-lead {
    margin-top: 8px;
    font-size: 15px;
  }

  .service-features {
    gap: 8px;
    margin-bottom: 18px;
  }

  .service-card button {
    min-height: 46px;
  }

  .final-cta-inner {
    padding-top: 30px;
  }

  .final-cta h2 {
    margin-bottom: 18px;
    font-size: clamp(26px, 8vw, 36px);
  }

  .hero-actions > *,
  .final-cta .primary-button {
    min-width: 0;
  }

  .final-cta .primary-button {
    width: 100%;
  }
}

@media (max-width: 380px) {
  .hero-actions {
    grid-template-columns: 1fr;
  }
}

/* 按钮专项：主次关系明确，按钮与纸张卡片使用同一组圆角和间距 */
.hero-actions {
  align-items: stretch;
  gap: var(--button-gap, 8px);
}

.hero-actions .primary-button,
.hero-actions .secondary-button {
  min-height: var(--button-height, 46px);
}

.service-card > button {
  min-height: var(--button-height, 46px);
  border-radius: var(--button-radius, 13px);
}

.final-cta .primary-button {
  min-width: 180px;
}

</style>
