<template>
  <div class="services">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link active">服务</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <h1>我们的服务</h1>
        <p>融合传统文化人格叙事与现代心理学工具<br>提供非医疗性质的个人成长支持</p>
      </div>
    </section>

    <!-- 服务详情 -->
    <section class="services-detail">
      <div class="container">
        <!-- 服务1 -->
        <div class="service-item">
          <div class="service-header">
            <h2>个人能量地图解读</h2>
            <div class="service-price">¥499 - ¥699</div>
          </div>
          <div class="service-body">
            <p class="service-intro">3-5页专业报告 + 60分钟深度解读</p>
            <h3>服务内容</h3>
            <ul class="service-list">
              <li>八字/紫微基础结构解读</li>
              <li>性格动力与能量模式分析</li>
              <li>关系模式深度剖析</li>
              <li>职业优势倾向评估</li>
              <li>当前困境中的心理议题识别</li>
            </ul>
            <h3>适合人群</h3>
            <p>初次接触个人成长咨询，希望快速了解自己能量特质和行为模式的你</p>
            <button class="service-cta">立即预约</button>
          </div>
        </div>

        <!-- 服务2 -->
        <div class="service-item featured">
          <div class="service-badge">推荐</div>
          <div class="service-header">
            <h2>个人成长深度咨询</h2>
            <div class="service-price">¥1599 - ¥3599</div>
          </div>
          <div class="service-body">
            <p class="service-intro">3-4次深度咨询 + 个性化成长方案</p>
            <h3>服务内容</h3>
            <ul class="service-list">
              <li>深度解读自我结构：原局能量完整分析</li>
              <li>自身模式和环境解读：能量消耗点识别</li>
              <li>关系模式深度探索：亲密关系、家庭、职场</li>
              <li>优势点挖掘：天赋能量与发展方向</li>
              <li>环境适配性评估：什么样的环境容易损耗能量</li>
              <li>个性化行动方案：可落地的成长策略</li>
            </ul>
            <h3>适合人群</h3>
            <p>处于人生转折期，面临重大选择，或长期困于某个议题需要系统性突破的你</p>
            <button class="service-cta primary">立即预约</button>
          </div>
        </div>

        <!-- 服务3 -->
        <div class="service-item">
          <div class="service-header">
            <h2>东方人格洞察入门课</h2>
            <div class="service-price">¥399 - ¥999</div>
          </div>
          <div class="service-body">
            <p class="service-intro">系统化课程 + 终身学习社群</p>
            <h3>课程内容</h3>
            <ul class="service-list">
              <li>命理与心理学融合工具体系</li>
              <li>理解自己的能量与关系模式</li>
              <li>系统化学习框架与方法论</li>
              <li>丰富的实用案例分析</li>
              <li>终身学习社群支持</li>
            </ul>
            <h3>适合人群</h3>
            <p>对自我探索有强烈兴趣，希望掌握工具自主成长，或未来从事相关领域的你</p>
            <button class="service-cta">查看课程</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 服务理念 -->
    <section class="service-philosophy">
      <div class="container">
        <h2>我们的理念</h2>
        <div class="philosophy-grid">
          <div class="philosophy-item">
            <div class="philosophy-icon">🎯</div>
            <h3>授人以渔</h3>
            <p>我们不倡导宿命论，命盘是带领我们更好认识自我的工具。真正认识自己，挖掘天赋能量，顺势而为，充分发挥主体性。</p>
          </div>
          <div class="philosophy-item">
            <div class="philosophy-icon">🗺️</div>
            <h3>个性化指南</h3>
            <p>融合东西方哲学智慧和工具，基于你真实的境遇，帮助你看到找到人生卡点、构建行动指南。</p>
          </div>
          <div class="philosophy-item">
            <div class="philosophy-icon">🔍</div>
            <h3>系统化分析</h3>
            <p>个人的成长与周遭他人息息相关，通过系统化整合分析，帮助个体找到现实能量消耗点、提供潜在行动修正方向。</p>
          </div>
          <div class="philosophy-item">
            <div class="philosophy-icon">🧭</div>
            <h3>从结构进入</h3>
            <p>我们从"结构"进入，看清人格地图。不同于心理咨询从具体"问题"进入，我们提供更宏观的视角。</p>
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
  name: 'Services'
}
</script>

<style scoped>
.services {
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
  font-size: 18px;
  color: #636e72;
  line-height: 1.8;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 服务详情 */
.services-detail {
  padding: 80px 0;
  background: #fff;
}

.service-item {
  background: #f8f9fa;
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 40px;
  position: relative;
  transition: all 0.3s;
}

.service-item:hover {
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.service-item.featured {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border: 2px solid #d4524f;
}

.service-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #d4524f;
  color: #fff;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.service-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  flex-wrap: wrap;
  gap: 20px;
}

.service-header h2 {
  font-size: 32px;
  font-weight: 700;
  color: #2d3436;
}

.service-price {
  font-size: 32px;
  font-weight: 700;
  color: #d4524f;
}

.service-body {
  color: #555;
}

.service-intro {
  font-size: 18px;
  color: #666;
  margin-bottom: 30px;
  font-weight: 500;
}

.service-body h3 {
  font-size: 20px;
  font-weight: 600;
  color: #2d3436;
  margin: 30px 0 15px;
}

.service-list {
  margin-bottom: 20px;
}

.service-list li {
  font-size: 16px;
  line-height: 2;
  padding-left: 25px;
  position: relative;
}

.service-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

.service-cta {
  margin-top: 30px;
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 600;
  color: #d4524f;
  border: 2px solid #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
  width: 100%;
  max-width: 200px;
}

.service-cta:hover {
  background: #d4524f;
  color: #fff;
  transform: translateY(-2px);
}

.service-cta.primary {
  background: #d4524f;
  color: #fff;
}

.service-cta.primary:hover {
  background: #c0392b;
}

/* 服务理念 */
.service-philosophy {
  padding: 80px 0;
  background: #f8f9fa;
}

.service-philosophy h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 60px;
  color: #2d3436;
}

.philosophy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 40px;
}

.philosophy-item {
  text-align: center;
  padding: 30px;
  background: #fff;
  border-radius: 15px;
  transition: all 0.3s;
}

.philosophy-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.philosophy-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.philosophy-item h3 {
  font-size: 22px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.philosophy-item p {
  font-size: 15px;
  line-height: 1.8;
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

  .services-detail {
    padding: 40px 0;
  }

  .service-item {
    padding: 30px 20px;
    margin-bottom: 30px;
  }

  .service-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .service-header h2 {
    font-size: 24px;
  }

  .service-price {
    font-size: 24px;
  }

  .service-badge {
    top: 15px;
    right: 15px;
    font-size: 12px;
    padding: 4px 12px;
  }

  .service-cta {
    max-width: 100%;
  }

  .service-philosophy {
    padding: 60px 0;
  }

  .service-philosophy h2 {
    font-size: 32px;
    margin-bottom: 40px;
  }

  .philosophy-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .philosophy-item {
    padding: 25px 20px;
  }
}
</style>
