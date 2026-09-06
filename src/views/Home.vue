<template>
  <div class="page-shell home">
    <BrandNav />

    <section class="landscape-hero hero">
      <div class="container hero-layout">
        <div class="hero-copy">
          <p class="section-kicker">CHENJIAN / LIFE ORIENTATION</p>
          <h1>星辰引路，<br />镜子照见</h1>
          <p class="hero-subtitle">
            星辰的运行规律，帮你照见人生选择的方向。辰鉴把个人属性、当下时序和后天行动放在同一张地图上。
          </p>
          <div class="hero-actions">
            <button class="primary-button" @click="goToAssessment">开始测评</button>
            <button class="secondary-button" @click="goToBooking">预约咨询</button>
          </div>
        </div>
        <div class="compass-visual" aria-hidden="true">
          <div class="compass-ring">
            <span class="needle"></span>
            <span class="center-dot"></span>
          </div>
          <p>定位此刻的卡点</p>
        </div>
      </div>
    </section>

    <section class="section-band intro-section">
      <div class="container intro-grid">
        <div>
          <p class="section-kicker">FOR THE STUCK MOMENT</p>
          <h2 class="section-title">不是安慰你，而是帮你看清自己为何停在这里</h2>
        </div>
        <div class="paper-card prose-card">
          <p>你不一定缺少努力，也不一定需要再听一句“你应该怎样”。很多时候，卡住是因为个人属性、环境时序和行动方式没有对上。</p>
          <p>辰鉴不替你评判人生，也不替你决定未来。我们先照见你是谁、当下处在哪个阶段，再一起找到更适合你的用力方式。</p>
          <p class="emphasis">社会属性可以被重新理解，个人属性值得被认真肯定。</p>
        </div>
      </div>
    </section>

    <section class="section-band alt">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">OUR METHOD</p>
          <h2 class="section-title">一张说明书，两个方向</h2>
          <p class="section-desc">
            fi 负责理解与定位，te 负责行动与决策。我们把八字、紫微、星盘等传统工具作为观察个人属性的透镜，再用心理学和哲学把洞察翻译成能使用的语言。
          </p>
        </div>
        <div class="method-grid">
          <article class="paper-card method-card">
            <span>FI / 01</span>
            <h3>我是谁</h3>
            <p>性格密码、天赋与暗面天赋、能量通路，以及你与关系的互动模式。</p>
          </article>
          <article class="paper-card method-card">
            <span>FI / 02</span>
            <h3>我卡在哪</h3>
            <p>看见当下核心矛盾、人生重复模式，以及潜意识正在保护什么。</p>
          </article>
          <article class="paper-card method-card">
            <span>TE / 03</span>
            <h3>我往哪去</h3>
            <p>从下周可做的三件事，到未来 6—12 个月的能力建设和决策日历。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band services-preview">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">SERVICE MAP</p>
          <h2 class="section-title">从照见自己，到把日子过好</h2>
        </div>
        <div class="services-grid">
          <article class="paper-card service-card">
            <span class="seal-badge">入门</span>
            <h3>辰鉴·人生说明书</h3>
            <p class="price">¥499 - ¥699</p>
            <ul class="service-features">
              <li>个人属性、天赋与能量通路</li>
              <li>核心矛盾与人生重复模式</li>
              <li>当前阶段的环境坐标</li>
            </ul>
            <button class="secondary-button" @click="goToBooking">了解详情</button>
          </article>
          <article class="paper-card service-card featured">
            <span class="seal-badge">推荐</span>
            <h3>辰鉴·行动与决策</h3>
            <p class="price">¥1599 - ¥3599</p>
            <ul class="service-features">
              <li>把说明书用于具体问题</li>
              <li>用舍由时，行藏在我</li>
              <li>个性化日历、陪伴与复盘</li>
            </ul>
            <button class="primary-button" @click="goToBooking">立即预约</button>
          </article>
          <article class="paper-card service-card">
            <span class="seal-badge">课程</span>
            <h3>辰鉴·共鉴计划</h3>
            <p class="price">¥399 - ¥999</p>
            <ul class="service-features">
              <li>玄学、心理学、哲学的分工</li>
              <li>从见自己到知行合一</li>
              <li>社群实践与真实案例共学</li>
            </ul>
            <button class="secondary-button" @click="goToCourse">查看课程</button>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band final-cta">
      <div class="container final-cta-inner">
        <p class="section-kicker">NEXT STEP</p>
        <h2>先写一页属于你的说明书</h2>
        <p>不算命，不评判，不替你预言未来。先从“我是谁”开始。</p>
        <button class="primary-button" @click="goToAssessment">开始探索</button>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
export default {
  name: 'Home',
  methods: {
    goToAssessment() {
      this.$router.push('/pages/assessment/assessment')
    },
    goToBooking() {
      this.$router.push('/pages/booking/booking')
    },
    goToCourse() {
      this.$router.push('/pages/course/course')
    }
  }
}
</script>

<style scoped>
.hero {
  min-height: max(640px, calc(100svh - var(--nav-height) - 56px));
  display: flex;
  align-items: center;
  padding: 56px 0 92px;
}

.hero-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  align-items: center;
  gap: 48px;
}

.hero-copy {
  width: 100%;
  max-width: 680px;
}

.hero h1 {
  width: 100%;
  max-width: 760px;
  color: var(--ink);
  font-size: clamp(46px, 8vw, 84px);
  font-weight: 900;
  line-height: 1.06;
  letter-spacing: 0.02em;
}

.hero-subtitle {
  width: 100%;
  max-width: 580px;
  margin-top: 24px;
  color: var(--ink-soft);
  font-size: clamp(17px, 2vw, 22px);
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  width: 100%;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 34px;
}

.hero-actions > * {
  min-width: 0;
}

.compass-visual {
  justify-self: end;
  display: grid;
  place-items: center;
  width: 260px;
  aspect-ratio: 1;
  border: 1px solid rgba(139, 90, 20, 0.18);
  border-radius: 50%;
  background: rgba(255, 252, 245, 0.34);
  box-shadow: var(--shadow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.64);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

.compass-ring {
  position: relative;
  width: 138px;
  aspect-ratio: 1;
  border: 1px solid rgba(184, 92, 80, 0.34);
  border-radius: 50%;
}

.compass-ring::before,
.compass-ring::after {
  content: "";
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  border: 1px solid rgba(217, 186, 98, 0.34);
}

.compass-ring::after {
  inset: 44px;
  background: rgba(184, 92, 80, 0.12);
}

.needle {
  position: absolute;
  left: 50%;
  top: 18px;
  width: 2px;
  height: 102px;
  border-radius: 999px;
  background: linear-gradient(var(--cinnabar-deep) 0 48%, var(--gold) 49% 100%);
  transform: translateX(-50%) rotate(24deg);
  transform-origin: 50% 50%;
}

.center-dot {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--cinnabar-deep);
  transform: translate(-50%, -50%);
}

.compass-visual p {
  margin-top: -22px;
  color: var(--gold-deep);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.intro-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 36px;
  align-items: start;
}

.prose-card {
  padding: clamp(24px, 4vw, 38px);
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.9;
}

.prose-card p + p {
  margin-top: 14px;
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

.method-card,
.service-card {
  padding: 26px;
}

.method-card span {
  color: rgba(184, 92, 80, 0.34);
  font-family: "Manrope", sans-serif;
  font-size: 38px;
  font-weight: 900;
}

.method-card h3,
.service-card h3 {
  margin-top: 14px;
  color: var(--ink);
  font-size: 22px;
  line-height: 1.35;
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
  font-family: "Manrope", "PingFang SC", sans-serif;
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

.footer {
  padding: 34px 0 calc(34px + var(--safe-bottom));
  text-align: center;
}

.version {
  margin-top: 8px;
  color: rgba(255, 250, 240, 0.46);
  font-family: "Manrope", sans-serif;
  font-size: 12px;
}

@media (max-width: 900px) {
  .hero-layout,
  .intro-grid {
    grid-template-columns: 1fr;
  }

  .compass-visual {
    justify-self: start;
    width: 196px;
  }

  .method-grid,
  .services-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .hero {
    min-height: max(680px, calc(100svh - var(--nav-height) - 64px));
    align-items: center;
    padding: 34px 0 38px;
  }

  .hero-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
  }

  .hero-copy {
    width: 100%;
  }

  .hero h1 {
    font-size: clamp(42px, 13vw, 56px);
    letter-spacing: 0;
    overflow-wrap: anywhere;
  }

  .hero-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 28px;
  }

  .hero-actions > * {
    width: 100%;
  }

  .compass-visual {
    width: 154px;
    margin-left: auto;
    opacity: 0.86;
  }

  .compass-ring {
    width: 86px;
  }

  .needle {
    top: 11px;
    height: 64px;
  }

  .compass-visual p {
    display: none;
  }

  .method-card,
  .service-card,
  .prose-card {
    padding: 22px;
  }

  .service-card {
    min-height: 0;
  }
}

@media (max-width: 380px) {
  .hero-actions {
    grid-template-columns: 1fr;
  }
}
</style>
