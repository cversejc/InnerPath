<template>
  <div class="page-shell services">
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link active">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link">测评</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <section class="page-header">
      <div class="container header-inner">
        <p class="section-kicker">SERVICE CATALOGUE</p>
        <h1>我们的服务</h1>
        <p>融合传统文化人格叙事与现代心理学工具，提供非医疗性质的个人成长支持。</p>
      </div>
    </section>

    <section class="section-band">
      <div class="container services-list">
        <article class="paper-card service-item">
          <div class="service-meta">
            <span class="seal-badge">基础解读</span>
            <p class="service-price">¥499 - ¥699</p>
          </div>
          <div class="service-copy">
            <h2>个人能量地图解读</h2>
            <p class="service-intro">3-5 页专业报告 + 60 分钟深度解读，适合第一次系统认识自己的人。</p>
            <div class="service-columns">
              <div>
                <h3>服务内容</h3>
                <ul class="service-list">
                  <li>八字 / 紫微基础结构解读</li>
                  <li>性格动力与能量模式分析</li>
                  <li>关系模式与职业优势倾向</li>
                  <li>当前困境中的心理议题识别</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>希望快速了解自身能量特质、行为模式和当下卡点的你。</p>
              </div>
            </div>
            <button class="secondary-button" @click="goToBooking">预约解读</button>
          </div>
        </article>

        <article class="paper-card service-item featured">
          <div class="service-meta">
            <span class="seal-badge">推荐方案</span>
            <p class="service-price">¥1599 - ¥3599</p>
          </div>
          <div class="service-copy">
            <h2>个人成长深度咨询</h2>
            <p class="service-intro">3-4 次深度咨询 + 个性化成长方案，适合处在人生转折期或长期困于同一议题的人。</p>
            <div class="service-columns">
              <div>
                <h3>服务内容</h3>
                <ul class="service-list">
                  <li>完整自我结构和原局能量分析</li>
                  <li>能量消耗点与环境适配评估</li>
                  <li>亲密关系、家庭、职场脚本探索</li>
                  <li>可落地的行动策略和复盘路径</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>面对重大选择、关系困境、职业转型或自我价值重建的人。</p>
              </div>
            </div>
            <button class="primary-button" @click="goToBooking">立即预约</button>
          </div>
        </article>

        <article class="paper-card service-item">
          <div class="service-meta">
            <span class="seal-badge">系统课程</span>
            <p class="service-price">¥399 - ¥999</p>
          </div>
          <div class="service-copy">
            <h2>东方人格洞察入门课</h2>
            <p class="service-intro">系统化课程 + 终身学习社群，适合想掌握工具、自主成长的人。</p>
            <div class="service-columns">
              <div>
                <h3>课程内容</h3>
                <ul class="service-list">
                  <li>命理与心理学融合工具体系</li>
                  <li>能量、关系与人格模式框架</li>
                  <li>实用案例分析和练习</li>
                  <li>学习社群持续支持</li>
                </ul>
              </div>
              <div>
                <h3>适合人群</h3>
                <p>对自我探索有强烈兴趣，或希望未来从事相关领域的人。</p>
              </div>
            </div>
            <button class="secondary-button" @click="goToCourse">查看课程</button>
          </div>
        </article>
      </div>
    </section>

    <section class="section-band alt philosophy-section">
      <div class="container">
        <div class="section-heading">
          <p class="section-kicker">PRINCIPLES</p>
          <h2 class="section-title">我们坚持的四件事</h2>
        </div>
        <div class="philosophy-grid">
          <article class="paper-card philosophy-item">
            <span>授人以渔</span>
            <p>命盘是认识自我的工具，不是决定人生的判决书。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>个性化指南</span>
            <p>基于真实处境，把抽象洞察翻译成个人行动地图。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>系统化分析</span>
            <p>从能量、关系、环境三层结构定位现实消耗点。</p>
          </article>
          <article class="paper-card philosophy-item">
            <span>从结构进入</span>
            <p>先看清人格地图，再处理具体问题。</p>
          </article>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 开启你的灵魂战略第一步。</p>
      </div>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'Services',
  methods: {
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
.page-header {
  padding: 92px 0 74px;
  text-align: center;
}

.header-inner {
  max-width: 780px;
}

.page-header h1 {
  max-width: 100%;
  color: var(--ink);
  font-size: clamp(42px, 8vw, 76px);
  line-height: 1.08;
}

.page-header p:not(.section-kicker) {
  max-width: 100%;
  margin-top: 20px;
  color: var(--ink-soft);
  font-size: 18px;
  line-height: 1.75;
}

.services-list {
  display: grid;
  gap: 20px;
}

.service-item {
  display: grid;
  min-width: 0;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 28px;
  padding: clamp(22px, 4vw, 34px);
}

.service-item.featured {
  border-color: rgba(184, 92, 80, 0.34);
  background:
    linear-gradient(180deg, rgba(255, 252, 245, 0.96), rgba(255, 239, 222, 0.82));
}

.service-meta {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
  border-right: 1px solid var(--line);
  padding-right: 24px;
}

.service-price {
  color: var(--cinnabar-deep);
  font-family: "Manrope", "PingFang SC", sans-serif;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.service-copy h2 {
  max-width: 100%;
  color: var(--ink);
  font-size: clamp(25px, 4vw, 38px);
  line-height: 1.18;
}

.service-intro {
  max-width: 760px;
  margin-top: 14px;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.75;
}

.service-columns {
  display: grid;
  min-width: 0;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 28px;
  margin-top: 28px;
}

.service-columns > * {
  min-width: 0;
}

.service-columns h3 {
  margin-bottom: 12px;
  color: var(--gold-deep);
  font-size: 15px;
  letter-spacing: 0.08em;
}

.service-columns p,
.service-list {
  color: var(--ink-soft);
  line-height: 1.75;
  overflow-wrap: anywhere;
}

.service-list {
  display: grid;
  gap: 8px;
}

.service-list li {
  position: relative;
  padding-left: 18px;
}

.service-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.72em;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gold);
}

.service-copy button {
  min-width: 190px;
  margin-top: 30px;
}

.section-heading {
  margin-bottom: 32px;
  text-align: center;
}

.philosophy-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.philosophy-item {
  padding: 22px;
}

.philosophy-item span {
  color: var(--cinnabar-deep);
  font-size: 18px;
  font-weight: 800;
}

.philosophy-item p {
  margin-top: 12px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.footer {
  padding: 34px 0 calc(34px + var(--safe-bottom));
  text-align: center;
}

@media (max-width: 900px) {
  .service-item,
  .service-columns {
    grid-template-columns: 1fr;
  }

  .service-meta {
    flex-direction: row;
    align-items: center;
    border-right: 0;
    border-bottom: 1px solid var(--line);
    padding-right: 0;
    padding-bottom: 18px;
  }

  .philosophy-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 767px) {
  .page-header {
    padding: 70px 0 48px;
  }

  .page-header p:not(.section-kicker) {
    font-size: 15px;
  }

  .service-item {
    gap: 20px;
  }

  .service-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .service-price {
    font-size: 24px;
  }

  .service-copy button {
    width: 100%;
  }

  .philosophy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
