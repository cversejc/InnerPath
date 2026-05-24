<template>
  <div class="home">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link active">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 主视觉区 -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">帮助你重构生命地图</h1>
        <p class="hero-subtitle">用传统文化中的人格叙事和现代心理学工具<br>理解自己的能量、关系和人生选择</p>
        <button class="cta-button" @click="goToAssessment">开始探索</button>
      </div>
    </section>

    <!-- 致这样的你 -->
    <section class="intro-section">
      <div class="container">
        <h2 class="section-title">致这样的你</h2>
        <div class="intro-content">
          <p>你是不是也这样——</p>
          <p>道理你都懂。</p>
          <p>各种课程、书籍、播客，你听过很多，也明白"要爱自己""要设立边界""要与原生家庭和解"。</p>
          <p>但你知道，有些东西不对。</p>
          <br>
          <p>那些不痛不痒的安慰，那些"一切都是最好的安排"的漂亮话，根本碰不到你心里最深的那个结。</p>
          <p>你试过心理咨询，但总觉得隔靴搔痒；你也悄悄看过星座命理，但又怕被人说"迷信"。</p>
          <p>你看起来一切正常，甚至在外人眼里过得还不错。</p>
          <p>但你自己知道：你被困住了。</p>
          <p>你在深夜问过自己无数次："为什么偏偏是此刻，我卡在了这里？"</p>
          <br>
          <p class="highlight">我们，就是为这样的你而来的。</p>
        </div>
      </div>
    </section>

    <!-- 我们是谁 -->
    <section class="about-section">
      <div class="container">
        <h2 class="section-title">我们是「离火引」</h2>
        <p class="section-desc">一个不提供"正确的废话"的灵魂战略咨询团队</p>
        <div class="about-content">
          <div class="about-item">
            <h3>我们跟别人不一样</h3>
            <p>我们不只想让你"感觉好一点"，我们想让你被深刻地理解。</p>
            <p>我们不想给你灌鸡汤，我们想给你一把能亲手解剖痛苦、重塑人生的手术刀。</p>
          </div>
          <div class="about-item">
            <h3>独创咨询体系</h3>
            <p>它不是纯心理的，因为有些潜意识，需要更古老的智慧才能照见；</p>
            <p>它也不是纯玄学的，因为我们绝不搞宿命论，我们只把八字斗数，当成帮你拍一张"灵魂X光片"的工具。</p>
          </div>
          <div class="about-item">
            <h3>我们不陪你原地打转</h3>
            <p>我们的咨询，最终会指向一套直指核心、可以落地的行动方案。</p>
            <p>我们不做你的拐杖，我们做你突破困局时，那张最精准的地图，那个最坚定的盟友。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 服务预览 -->
    <section class="services-preview">
      <div class="container">
        <h2 class="section-title">我们的服务</h2>
        <div class="services-grid">
          <div class="service-card">
            <h3>个人能量地图解读</h3>
            <p class="price">¥499 - ¥699</p>
            <ul class="service-features">
              <li>八字/紫微基础结构解读</li>
              <li>性格动力与能量模式</li>
              <li>关系模式分析</li>
              <li>职业优势倾向</li>
              <li>当前困境中的心理议题</li>
            </ul>
            <button class="service-button" @click="goToBooking">了解详情</button>
          </div>
          <div class="service-card featured">
            <h3>个人成长深度咨询</h3>
            <p class="price">¥1599 - ¥3599</p>
            <ul class="service-features">
              <li>深度解读自我结构</li>
              <li>能量消耗点分析</li>
              <li>关系与优势点解读</li>
              <li>环境适配性评估</li>
              <li>个性化行动方案</li>
            </ul>
            <button class="service-button" @click="goToBooking">立即预约</button>
          </div>
          <div class="service-card">
            <h3>东方人格洞察入门课</h3>
            <p class="price">¥399 - ¥999</p>
            <ul class="service-features">
              <li>命理与心理学融合工具</li>
              <li>理解能量与关系模式</li>
              <li>系统化学习框架</li>
              <li>实用案例分析</li>
              <li>终身学习社群</li>
            </ul>
            <button class="service-button" @click="goToCourse">查看课程</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 欢迎来到「离火引」，开启你的"灵魂战略"第一步。</p>
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
.home {
  width: 100%;
}

/* 导航栏 */
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 24px;
  font-weight: 600;
  color: #d4524f;
}

.nav-menu {
  display: flex;
  gap: 40px;
}

.nav-link {
  font-size: 16px;
  color: #666;
  transition: color 0.3s;
}

.nav-link:hover,
.nav-link.active {
  color: #d4524f;
}

/* 主视觉区 */
.hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
  padding: 100px 40px 60px;
}

.hero-content {
  text-align: center;
  max-width: 800px;
}

.hero-title {
  font-size: 56px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 30px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 20px;
  color: #636e72;
  margin-bottom: 50px;
  line-height: 1.8;
}

.cta-button {
  padding: 16px 48px;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  background: #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.cta-button:hover {
  background: #c0392b;
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(212, 82, 79, 0.3);
}

/* 通用容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 40px;
}

/* 通用区块 */
section {
  padding: 100px 0;
}

.section-title {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 60px;
  color: #2d3436;
}

.section-desc {
  font-size: 20px;
  text-align: center;
  color: #636e72;
  margin-top: -40px;
  margin-bottom: 60px;
}

/* 介绍区块 */
.intro-section {
  background: #f8f9fa;
}

.intro-content {
  max-width: 800px;
  margin: 0 auto;
  font-size: 18px;
  line-height: 2;
  color: #555;
}

.intro-content p {
  margin-bottom: 10px;
}

.intro-content .highlight {
  font-size: 22px;
  font-weight: 600;
  color: #d4524f;
  margin-top: 20px;
}

/* 关于区块 */
.about-section {
  background: #fff;
}

.about-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
  margin-top: 60px;
}

.about-item h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 20px;
}

.about-item p {
  font-size: 16px;
  line-height: 1.8;
  color: #666;
  margin-bottom: 15px;
}

/* 服务预览 */
.services-preview {
  background: #f8f9fa;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 40px;
}

.service-card {
  background: #fff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.service-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.12);
}

.service-card.featured {
  border: 2px solid #d4524f;
  position: relative;
}

.service-card h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 20px;
}

.price {
  font-size: 28px;
  font-weight: 700;
  color: #d4524f;
  margin-bottom: 30px;
}

.service-features {
  margin-bottom: 30px;
}

.service-features li {
  font-size: 16px;
  color: #666;
  margin-bottom: 12px;
  padding-left: 20px;
  position: relative;
}

.service-features li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

.service-button {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  color: #d4524f;
  border: 2px solid #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.service-button:hover {
  background: #d4524f;
  color: #fff;
}

/* 页脚 */
.footer {
  background: #2d3436;
  padding: 40px 0;
  text-align: center;
  color: #b2bec3;
}

.footer .version {
  margin-top: 10px;
  font-size: 12px;
  color: #636e72;
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-container {
    padding: 15px 20px;
  }

  .nav-menu {
    gap: 20px;
  }

  .hero {
    padding: 80px 20px 40px;
  }

  .hero-title {
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .section-title {
    font-size: 32px;
  }

  .container {
    padding: 0 20px;
  }

  section {
    padding: 60px 0;
  }

  .services-grid {
    grid-template-columns: 1fr;
  }
}
</style>
