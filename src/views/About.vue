<template>
  <div class="about">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link active">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <h1>关于我们</h1>
        <p>一个不提供"正确的废话"的灵魂战略咨询团队</p>
      </div>
    </section>

    <!-- 我们的故事 -->
    <section class="our-story">
      <div class="container">
        <h2 class="section-title">我们的故事</h2>
        <div class="story-content">
          <p>我们的创始人，和你一样，也曾卡在人生的至暗时刻。</p>
          <p>他因独特的思考方式与旧规则激烈冲突，最终从顶尖学府的心理学象牙塔里破茧而出。</p>
          <p>他把自己的天赋——像海一样深沉的共情、像刀一样锋利的洞察、还有那种能把一切旧认知彻底重构的抽离思维——全部打磨成了产品。</p>
        </div>
      </div>
    </section>

    <!-- 我们的方法 -->
    <section class="our-method">
      <div class="container">
        <h2 class="section-title">我们的方法</h2>
        <div class="method-content">
          <div class="method-item">
            <div class="method-number">01</div>
            <h3>独创咨询体系</h3>
            <p>它不是纯心理的，因为有些潜意识，需要更古老的智慧才能照见；它也不是纯玄学的，因为我们绝不搞宿命论，我们只把八字斗数，当成帮你拍一张"灵魂X光片"的工具。</p>
          </div>
          <div class="method-item">
            <div class="method-number">02</div>
            <h3>定位困境坐标</h3>
            <p>我们用这套东西，来定位你困境的时空坐标，来命名你内心那场看不见的战争。</p>
          </div>
          <div class="method-item">
            <div class="method-number">03</div>
            <h3>可落地的行动方案</h3>
            <p>我们的咨询，最终会指向一套直指核心、可以落地的行动方案。我们不做你的拐杖，我们做你突破困局时，那张最精准的地图，那个最坚定的盟友。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 我们的差异化 -->
    <section class="our-difference">
      <div class="container">
        <h2 class="section-title">我们的差异化</h2>
        <div class="difference-grid">
          <div class="difference-card">
            <h3>vs 传统心理咨询</h3>
            <ul>
              <li><span class="label">入门门槛：</span>我们不要求你"有问题"才能来</li>
              <li><span class="label">文化适配：</span>东方文化语境下的本土化工具</li>
              <li><span class="label">效率：</span>命盘提供宏观视角，快速定位核心议题</li>
              <li><span class="label">深度：</span>从结构进入，而非单一问题</li>
            </ul>
          </div>
          <div class="difference-card">
            <h3>vs 传统命理</h3>
            <ul>
              <li><span class="label">去神秘化：</span>科学化的解读框架</li>
              <li><span class="label">主体性：</span>强调个人成长性，而非宿命论</li>
              <li><span class="label">可落地：</span>提供心理支持和行动方案</li>
              <li><span class="label">专业性：</span>结合现代心理学工具</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- 适合你吗 -->
    <section class="for-you">
      <div class="container">
        <h2 class="section-title">如果你也有这样的感觉</h2>
        <div class="for-you-content">
          <div class="for-you-item">
            <div class="icon">🔍</div>
            <p>你对人性和成长有强烈的探索欲，早已厌倦了浅层的安慰</p>
          </div>
          <div class="for-you-item">
            <div class="icon">🌟</div>
            <p>你正处在职业、关系或人生意义的艰难转型期，旧地图已经彻底失效</p>
          </div>
          <div class="for-you-item">
            <div class="icon">💫</div>
            <p>你心里清楚自己"不一样"，渴望被一个真正懂你的人，深度地看见</p>
          </div>
        </div>
        <div class="for-you-cta">
          <p class="highlight">那么，你就是我们一直在等的人。</p>
          <p class="tagline">这里不谈"更好的自己"，我们只谈——如何让你，真正成为你自己。</p>
          <button class="cta-button">开始你的探索之旅</button>
        </div>
      </div>
    </section>

    <!-- 联系我们 -->
    <section class="contact">
      <div class="container">
        <h2 class="section-title">联系我们</h2>
        <div class="contact-content">
          <div class="contact-item">
            <h3>预约咨询</h3>
            <p>微信：innerseek2026</p>
          </div>
          <div class="contact-item">
            <h3>合作咨询</h3>
            <p>邮箱：hello@innerseek.me</p>
          </div>
          <div class="contact-item">
            <h3>关注我们</h3>
            <p>公众号：离火引InnerSeek</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <p>&copy; 2026 离火引 InnerSeek. 欢迎来到「离火引」，开启你的"灵魂战略"第一步。</p>
      </div>
    </footer>
  </div>
</template>

<script>
export default {
  name: 'About'
}
</script>

<style scoped>
.about {
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

/* 页面标题 */
.page-header {
  padding: 140px 20px 80px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
  text-align: center;
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 20px;
}

.page-header p {
  font-size: 20px;
  color: #636e72;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

section {
  padding: 80px 0;
}

.section-title {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 60px;
  color: #2d3436;
}

/* 我们的故事 */
.our-story {
  background: #fff;
}

.story-content {
  max-width: 800px;
  margin: 0 auto;
  font-size: 18px;
  line-height: 2;
  color: #555;
}

.story-content p {
  margin-bottom: 20px;
}

/* 我们的方法 */
.our-method {
  background: #f8f9fa;
}

.method-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
}

.method-item {
  background: #fff;
  padding: 40px;
  border-radius: 15px;
  transition: all 0.3s;
}

.method-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.method-number {
  font-size: 48px;
  font-weight: 700;
  color: #d4524f;
  opacity: 0.2;
  margin-bottom: 20px;
}

.method-item h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.method-item p {
  font-size: 16px;
  line-height: 1.8;
  color: #666;
}

/* 差异化 */
.our-difference {
  background: #fff;
}

.difference-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 40px;
}

.difference-card {
  background: #f8f9fa;
  padding: 40px;
  border-radius: 15px;
  border: 2px solid transparent;
  transition: all 0.3s;
}

.difference-card:hover {
  border-color: #d4524f;
  box-shadow: 0 10px 30px rgba(212, 82, 79, 0.1);
}

.difference-card h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #d4524f;
}

.difference-card ul li {
  font-size: 16px;
  line-height: 2.2;
  color: #555;
  margin-bottom: 12px;
}

.difference-card .label {
  font-weight: 600;
  color: #d4524f;
}

/* 适合你吗 */
.for-you {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
}

.for-you-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 30px;
  margin-bottom: 60px;
}

.for-you-item {
  background: #fff;
  padding: 30px;
  border-radius: 15px;
  text-align: center;
  transition: all 0.3s;
}

.for-you-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.for-you-item .icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.for-you-item p {
  font-size: 16px;
  line-height: 1.8;
  color: #555;
}

.for-you-cta {
  text-align: center;
  max-width: 700px;
  margin: 0 auto;
}

.for-you-cta .highlight {
  font-size: 28px;
  font-weight: 600;
  color: #d4524f;
  margin-bottom: 20px;
}

.for-you-cta .tagline {
  font-size: 20px;
  color: #555;
  margin-bottom: 40px;
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

/* 联系我们 */
.contact {
  background: #fff;
}

.contact-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 40px;
}

.contact-item {
  text-align: center;
  padding: 30px;
  background: #f8f9fa;
  border-radius: 15px;
}

.contact-item h3 {
  font-size: 22px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.contact-item p {
  font-size: 16px;
  color: #666;
}

/* 页脚 */
.footer {
  background: #2d3436;
  padding: 40px 0;
  text-align: center;
  color: #b2bec3;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .nav-container {
    padding: 15px 20px;
  }

  .nav-menu {
    gap: 15px;
  }

  .nav-link {
    font-size: 14px;
  }

  .page-header {
    padding: 100px 20px 60px;
  }

  .page-header h1 {
    font-size: 32px;
  }

  .page-header p {
    font-size: 16px;
  }

  section {
    padding: 60px 0;
  }

  .section-title {
    font-size: 28px;
    margin-bottom: 40px;
  }

  .story-content {
    font-size: 16px;
  }

  .method-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .method-item {
    padding: 30px 20px;
  }

  .difference-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .difference-card {
    padding: 30px 20px;
  }

  .for-you-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .for-you-cta .highlight {
    font-size: 22px;
  }

  .for-you-cta .tagline {
    font-size: 16px;
  }

  .contact-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
</style>
