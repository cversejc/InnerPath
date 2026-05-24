<template>
  <div class="course">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/services/services" class="nav-link">服务</router-link></li>
          <li><router-link to="/pages/assessment/assessment" class="nav-link">能量测评</router-link></li>
          <li><router-link to="/pages/course/course" class="nav-link active">课程</router-link></li>
          <li><router-link to="/pages/about/about" class="nav-link">关于</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <h1>东方人格洞察入门课</h1>
        <p>融合传统文化与现代心理学<br>掌握工具，开启自主成长之旅</p>
      </div>
    </section>

    <!-- 课程介绍 -->
    <section class="course-intro">
      <div class="container">
        <div class="intro-content">
          <div class="intro-text">
            <h2>为什么要学习这门课？</h2>
            <p>在AI时代，技能会被替代，但理解自己、理解人性的能力永远不会过时。</p>
            <p>这门课不是教你"算命"，而是教你用东方智慧的人格分析工具，结合现代心理学，建立一套属于自己的"自我认知系统"。</p>
            <ul class="intro-benefits">
              <li>🎯 理解自己的能量模式与行为倾向</li>
              <li>🔍 看清关系中的互动模式</li>
              <li>💡 找到适合自己的成长路径</li>
              <li>🛠️ 掌握可持续使用的分析工具</li>
            </ul>
          </div>
          <div class="intro-image">
            <div class="course-card-preview">
              <div class="preview-badge">系统化课程</div>
              <h3>东方人格洞察</h3>
              <div class="preview-stats">
                <div class="stat-item">
                  <div class="stat-number">12+</div>
                  <div class="stat-label">课时</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">终身</div>
                  <div class="stat-label">回看</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">社群</div>
                  <div class="stat-label">支持</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 课程大纲 -->
    <section class="course-outline">
      <div class="container">
        <h2>课程大纲</h2>
        <p class="section-desc">系统化学习，从理论到实践</p>

        <div class="modules">
          <div class="module-item" v-for="(module, index) in modules" :key="index">
            <div class="module-header" @click="toggleModule(index)">
              <div class="module-title">
                <span class="module-number">模块 {{ index + 1 }}</span>
                <h3>{{ module.title }}</h3>
              </div>
              <span class="module-toggle">{{ expandedModules.includes(index) ? '−' : '+' }}</span>
            </div>
            <div class="module-content" v-show="expandedModules.includes(index)">
              <p class="module-desc">{{ module.description }}</p>
              <ul class="lesson-list">
                <li v-for="(lesson, lIndex) in module.lessons" :key="lIndex">
                  <span class="lesson-icon">📖</span>
                  <span class="lesson-title">{{ lesson }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 适合人群 -->
    <section class="target-audience">
      <div class="container">
        <h2>这门课适合谁？</h2>
        <div class="audience-grid">
          <div class="audience-card">
            <div class="audience-icon">🌱</div>
            <h3>自我探索者</h3>
            <p>对自我认知有强烈兴趣，希望深入了解自己的能量特质和行为模式</p>
          </div>
          <div class="audience-card">
            <div class="audience-icon">🎓</div>
            <h3>心理学爱好者</h3>
            <p>想要学习东方人格分析工具，拓展心理学视野和实践方法</p>
          </div>
          <div class="audience-card">
            <div class="audience-icon">💼</div>
            <h3>职业发展者</h3>
            <p>希望通过了解自己的天赋优势，找到更适合的职业发展方向</p>
          </div>
          <div class="audience-card">
            <div class="audience-icon">👥</div>
            <h3>关系经营者</h3>
            <p>想要理解关系模式，改善亲密关系、家庭关系或职场关系</p>
          </div>
          <div class="audience-card">
            <div class="audience-icon">🔮</div>
            <h3>传统文化爱好者</h3>
            <p>对八字、紫微等传统文化感兴趣，希望系统化学习并应用于现代生活</p>
          </div>
          <div class="audience-card">
            <div class="audience-icon">🚀</div>
            <h3>未来从业者</h3>
            <p>计划从事个人成长、咨询相关领域，需要掌握专业工具和方法论</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 课程特色 -->
    <section class="course-features">
      <div class="container">
        <h2>课程特色</h2>
        <div class="features-grid">
          <div class="feature-item">
            <div class="feature-icon">🎯</div>
            <h3>理论与实践结合</h3>
            <p>不只讲理论，更注重实际应用。每个模块都配有案例分析和练习</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🌉</div>
            <h3>东西方融合</h3>
            <p>将传统命理智慧与现代心理学工具结合，建立本土化的人格分析体系</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔄</div>
            <h3>终身学习社群</h3>
            <p>加入学习社群，持续交流、案例研讨、答疑解惑</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">📚</div>
            <h3>系统化方法论</h3>
            <p>不是碎片化知识，而是完整的分析框架和可复用的工具体系</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 价格与报名 -->
    <section class="course-pricing">
      <div class="container">
        <h2>课程价格</h2>
        <div class="pricing-cards">
          <div class="pricing-card">
            <div class="pricing-badge">早鸟价</div>
            <h3>基础版</h3>
            <div class="price">
              <span class="price-amount">¥399</span>
              <span class="price-original">¥599</span>
            </div>
            <ul class="pricing-includes">
              <li>完整课程视频</li>
              <li>课程配套资料</li>
              <li>终身回看权限</li>
              <li>学习社群</li>
            </ul>
            <button class="btn-enroll">立即报名</button>
          </div>

          <div class="pricing-card featured">
            <div class="pricing-badge recommended">推荐</div>
            <h3>进阶版</h3>
            <div class="price">
              <span class="price-amount">¥699</span>
              <span class="price-original">¥999</span>
            </div>
            <ul class="pricing-includes">
              <li>基础版全部内容</li>
              <li>1次个人案例解读</li>
              <li>进阶学习资料包</li>
              <li>优先答疑权限</li>
              <li>线下活动优先参与</li>
            </ul>
            <button class="btn-enroll primary">立即报名</button>
          </div>

          <div class="pricing-card">
            <div class="pricing-badge">限量</div>
            <h3>VIP版</h3>
            <div class="price">
              <span class="price-amount">¥999</span>
            </div>
            <ul class="pricing-includes">
              <li>进阶版全部内容</li>
              <li>3次1对1深度答疑</li>
              <li>专属学习计划</li>
              <li>未来课程优惠</li>
              <li>咨询师认证路径</li>
            </ul>
            <button class="btn-enroll">立即报名</button>
          </div>
        </div>

        <div class="enrollment-notice">
          <p>💡 报名后即可开始学习，课程持续更新中</p>
          <p>📧 报名咨询请联系：innerseek@example.com</p>
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
  name: 'Course',
  data() {
    return {
      expandedModules: [0],
      modules: [
        {
          title: '基础篇：东方人格分析的哲学基础',
          description: '理解阴阳五行、天干地支的底层逻辑，建立东方思维框架',
          lessons: [
            '阴阳五行：不是迷信，是系统思维',
            '天干地支：时间节律与能量周期',
            '东方哲学与现代心理学的对话',
            '如何科学地看待传统命理工具'
          ]
        },
        {
          title: '工具篇：八字基础与能量解读',
          description: '学习八字排盘、十神系统，理解个人能量结构',
          lessons: [
            '八字排盘：如何读懂你的"时间密码"',
            '十神系统：理解你的心理动力模式',
            '五行平衡：能量流通与淤堵',
            '格局分析：看清你的能量结构',
            '案例实战：真实案例解读练习'
          ]
        },
        {
          title: '工具篇：紫微斗数与关系模式',
          description: '学习紫微斗数，深入理解关系互动与人生议题',
          lessons: [
            '紫微斗数排盘基础',
            '十二宫位：人生各领域的能量分布',
            '主星特质：理解不同的人格类型',
            '关系宫位：看清你的关系模式',
            '案例实战：关系议题分析'
          ]
        },
        {
          title: '整合篇：心理学视角的命理解读',
          description: '将命理语言转化为心理学语言，建立实用的分析框架',
          lessons: [
            '从命理到心理：语言转译系统',
            '人格特质分析：五大维度整合',
            '行为模式识别：看见重复的模式',
            '防御机制与应对策略',
            '成长路径规划：从认知到行动'
          ]
        },
        {
          title: '应用篇：人生议题的实战分析',
          description: '针对职业、关系、自我价值等议题的具体应用',
          lessons: [
            '职业发展：找到你的天赋优势',
            '亲密关系：理解关系中的互动模式',
            '家庭议题：原生家庭的影响与超越',
            '自我价值：建立内在稳定感',
            '综合案例：完整的咨询流程演示'
          ]
        },
        {
          title: '进阶篇：成为自己的咨询师',
          description: '掌握自我分析与持续成长的方法',
          lessons: [
            '如何为自己做定期复盘',
            '流年运势：理解周期与节奏',
            '行动方案制定：从认知到改变',
            '持续学习：建立你的知识体系',
            '未来发展：咨询师成长路径'
          ]
        }
      ]
    }
  },
  methods: {
    toggleModule(index) {
      const pos = this.expandedModules.indexOf(index)
      if (pos > -1) {
        this.expandedModules.splice(pos, 1)
      } else {
        this.expandedModules.push(index)
      }
    }
  }
}
</script>

<style scoped>
.course {
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
  gap: 30px;
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

/* 课程介绍 */
.course-intro {
  padding: 80px 0;
  background: #fff;
}

.intro-content {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 60px;
  align-items: center;
}

.intro-text h2 {
  font-size: 32px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 20px;
}

.intro-text p {
  font-size: 16px;
  line-height: 1.8;
  color: #666;
  margin-bottom: 15px;
}

.intro-benefits {
  margin-top: 30px;
}

.intro-benefits li {
  font-size: 16px;
  line-height: 2.2;
  color: #555;
}

.course-card-preview {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  padding: 40px;
  border-radius: 20px;
  border: 2px solid #d4524f;
  position: relative;
}

.preview-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #d4524f;
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.course-card-preview h3 {
  font-size: 28px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 30px;
  text-align: center;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: #d4524f;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

/* 课程大纲 */
.course-outline {
  padding: 80px 0;
  background: #f8f9fa;
}

.course-outline h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: #2d3436;
  margin-bottom: 15px;
}

.section-desc {
  text-align: center;
  color: #666;
  font-size: 16px;
  margin-bottom: 50px;
}

.modules {
  max-width: 900px;
  margin: 0 auto;
}

.module-item {
  background: #fff;
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
  border: 2px solid #e0e0e0;
  transition: all 0.3s;
}

.module-item:hover {
  border-color: #d4524f;
}

.module-header {
  padding: 25px 30px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s;
}

.module-header:hover {
  background: #f8f9fa;
}

.module-title {
  display: flex;
  align-items: center;
  gap: 15px;
}

.module-number {
  background: #d4524f;
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.module-title h3 {
  font-size: 20px;
  font-weight: 600;
  color: #2d3436;
}

.module-toggle {
  font-size: 28px;
  color: #d4524f;
  font-weight: 300;
}

.module-content {
  padding: 0 30px 25px;
  border-top: 1px solid #f0f0f0;
}

.module-desc {
  font-size: 15px;
  color: #666;
  margin: 20px 0;
  line-height: 1.6;
}

.lesson-list li {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: #555;
}

.lesson-list li:last-child {
  border-bottom: none;
}

.lesson-icon {
  font-size: 18px;
}

/* 适合人群 */
.target-audience {
  padding: 80px 0;
  background: #fff;
}

.target-audience h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: #2d3436;
  margin-bottom: 50px;
}

.audience-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.audience-card {
  background: #f8f9fa;
  padding: 30px;
  border-radius: 15px;
  text-align: center;
  transition: all 0.3s;
}

.audience-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.audience-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.audience-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.audience-card p {
  font-size: 14px;
  line-height: 1.7;
  color: #666;
}

/* 课程特色 */
.course-features {
  padding: 80px 0;
  background: #f8f9fa;
}

.course-features h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: #2d3436;
  margin-bottom: 50px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 40px;
}

.feature-item {
  text-align: center;
}

.feature-icon {
  font-size: 56px;
  margin-bottom: 20px;
}

.feature-item h3 {
  font-size: 22px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 15px;
}

.feature-item p {
  font-size: 15px;
  line-height: 1.7;
  color: #666;
}

/* 价格 */
.course-pricing {
  padding: 80px 0;
  background: #fff;
}

.course-pricing h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: #2d3436;
  margin-bottom: 50px;
}

.pricing-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
  max-width: 1100px;
  margin: 0 auto 40px;
}

.pricing-card {
  background: #f8f9fa;
  border-radius: 20px;
  padding: 40px;
  position: relative;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.pricing-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.1);
  border-color: #d4524f;
}

.pricing-card.featured {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border-color: #d4524f;
}

.pricing-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: #666;
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.pricing-badge.recommended {
  background: #d4524f;
}

.pricing-card h3 {
  font-size: 24px;
  font-weight: 600;
  color: #2d3436;
  margin-bottom: 20px;
  text-align: center;
}

.price {
  text-align: center;
  margin-bottom: 30px;
}

.price-amount {
  font-size: 36px;
  font-weight: 700;
  color: #d4524f;
}

.price-original {
  font-size: 18px;
  color: #999;
  text-decoration: line-through;
  margin-left: 10px;
}

.pricing-includes {
  margin-bottom: 30px;
}

.pricing-includes li {
  font-size: 15px;
  color: #666;
  line-height: 2;
  padding-left: 20px;
  position: relative;
}

.pricing-includes li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

.btn-enroll {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  color: #d4524f;
  border: 2px solid #d4524f;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-enroll:hover {
  background: #d4524f;
  color: #fff;
}

.btn-enroll.primary {
  background: #d4524f;
  color: #fff;
}

.btn-enroll.primary:hover {
  background: #c0392b;
}

.enrollment-notice {
  text-align: center;
  margin-top: 40px;
}

.enrollment-notice p {
  font-size: 15px;
  color: #666;
  margin-bottom: 10px;
}

/* 页脚 */
.footer {
  background: #2d3436;
  padding: 40px 0;
  text-align: center;
  color: #b2bec3;
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-container {
    padding: 15px 20px;
  }

  .nav-menu {
    gap: 12px;
  }

  .nav-link {
    font-size: 13px;
  }

  .page-header {
    padding: 100px 20px 60px;
  }

  .page-header h1 {
    font-size: 32px;
  }

  .intro-content {
    grid-template-columns: 1fr;
  }

  .course-outline,
  .target-audience,
  .course-features,
  .course-pricing {
    padding: 60px 0;
  }

  .course-outline h2,
  .target-audience h2,
  .course-features h2,
  .course-pricing h2 {
    font-size: 32px;
  }

  .audience-grid,
  .pricing-cards {
    grid-template-columns: 1fr;
  }

  .module-header {
    padding: 20px;
  }

  .module-content {
    padding: 0 20px 20px;
  }
}
</style>
