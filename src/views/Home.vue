<template>
  <div class="page-shell home">
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link active">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link">测评</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <section class="landscape-hero hero">
      <div class="container hero-layout">
        <div class="hero-copy">
          <p class="section-kicker">INNERSEEK COMPASS</p>
          <h1>帮助你重构生命地图</h1>
          <p class="hero-subtitle">
            用传统人格叙事和现代心理学工具，看见能量、关系与选择背后的结构。
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
          <p>你听过很多道理，也明白要爱自己、设立边界、与过去和解。</p>
          <p>但那些漂亮话没有碰到真正的结。你看起来一切正常，心里却知道自己被困住了。</p>
          <p class="emphasis">离火引为这样的时刻而来：把混乱变成地图，把感受落成行动。</p>
        </div>
      </div>
    </section>

    <section class="section-band alt">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">OUR METHOD</p>
          <h2 class="section-title">从结构进入，而不是原地打转</h2>
          <p class="section-desc">
            我们把八字、紫微等传统工具作为人格结构的透镜，再用现代心理学语言转译为可执行的成长策略。
          </p>
        </div>
        <div class="method-grid">
          <article class="paper-card method-card">
            <span>01</span>
            <h3>看见能量结构</h3>
            <p>识别你的动力来源、消耗点和反复出现的选择模式。</p>
          </article>
          <article class="paper-card method-card">
            <span>02</span>
            <h3>命名关系脚本</h3>
            <p>把亲密关系、家庭和职场里的隐性互动模式说清楚。</p>
          </article>
          <article class="paper-card method-card">
            <span>03</span>
            <h3>落成行动方案</h3>
            <p>不做宿命论，把洞察转化为能执行、能复盘的下一步。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band services-preview">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">SERVICE MAP</p>
          <h2 class="section-title">选择一张适合此刻的地图</h2>
        </div>
        <div class="services-grid">
          <article class="paper-card service-card">
            <span class="seal-badge">入门</span>
            <h3>个人能量地图解读</h3>
            <p class="price">¥499 - ¥699</p>
            <ul class="service-features">
              <li>八字 / 紫微基础结构解读</li>
              <li>性格动力与关系模式分析</li>
              <li>当前困境中的心理议题定位</li>
            </ul>
            <button class="secondary-button" @click="goToBooking">了解详情</button>
          </article>
          <article class="paper-card service-card featured">
            <span class="seal-badge">推荐</span>
            <h3>个人成长深度咨询</h3>
            <p class="price">¥1599 - ¥3599</p>
            <ul class="service-features">
              <li>完整自我结构和消耗点分析</li>
              <li>关系、职业与环境适配评估</li>
              <li>个性化行动方案和复盘路径</li>
            </ul>
            <button class="primary-button" @click="goToBooking">立即预约</button>
          </article>
          <article class="paper-card service-card">
            <span class="seal-badge">课程</span>
            <h3>东方人格洞察入门课</h3>
            <p class="price">¥399 - ¥999</p>
            <ul class="service-features">
              <li>命理与心理学融合工具</li>
              <li>系统化学习框架与案例</li>
              <li>终身学习社群支持</li>
            </ul>
            <button class="secondary-button" @click="goToCourse">查看课程</button>
          </article>
        </div>
      </div>
    </section>

    <section class="section-band final-cta">
      <div class="container final-cta-inner">
        <p class="section-kicker">NEXT STEP</p>
        <h2>先测一张属于你的能量地图</h2>
        <button class="primary-button" @click="goToAssessment">开始探索</button>
      </div>
    </section>

    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 开启你的灵魂战略第一步。</p>
        <p class="version">v{{ version }}</p>
      </div>
    </footer>
  </div>
</template>

<script>
import pkg from '../../package.json'

export default {
  name: 'Home',
  data() {
    return {
      version: pkg.version
    }
  },
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
