<template>
  <div class="course">
    <BrandNav />

    <!-- 页面标题 -->
    <section class="page-header">
      <div class="container">
        <p class="section-kicker">CHENJIAN / CO-EXPLORATION</p>
        <h1>辰鉴·共鉴计划</h1>
        <p>把玄学、心理学与哲学放回生活<br>在长期的人本实践里，学会见自己、知其序、行其路</p>
      </div>
    </section>

    <!-- 课程介绍 -->
    <section class="course-intro">
      <div class="container">
        <div class="intro-content">
          <div class="intro-text">
            <h2>为什么要加入共鉴？</h2>
            <p>在一个越来越快、越来越功利的社会里，理解自己、理解关系、理解时序，是不容易被替代的长期能力。</p>
            <p>共鉴不教人给自己或别人下判断，而是练习如何把传统智慧翻译成现代生活能使用的语言，建立一套属于自己的“人生观察系统”。</p>
            <ul class="intro-benefits">
              <li><IconMark name="self" />读懂自己的性格密码与天赋</li>
              <li><IconMark name="relationship" />看见关系与人生重复模式</li>
              <li><IconMark name="spark" />在不同阶段找到合适的用力方式</li>
              <li><IconMark name="settings" />用记录、日历和复盘把洞察落地</li>
            </ul>
          </div>
          <div class="intro-image">
            <div class="course-card-preview">
              <div class="preview-badge">理论 × 实践 × 陪伴</div>
              <h3>辰鉴共鉴</h3>
              <div class="preview-stats">
                <div class="stat-item">
                  <div class="stat-number">12+</div>
                  <div class="stat-label">主题</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">终身</div>
                  <div class="stat-label">记录</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">社群</div>
                  <div class="stat-label">同行</div>
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
        <h2>共鉴路径</h2>
        <p class="section-desc">不追求一次学会，追求每次都能在生活里多看见一点。</p>

        <div class="modules">
          <div class="module-item" v-for="(module, index) in modules" :key="index">
            <button
              type="button"
              class="module-header"
              :aria-expanded="expandedModules.includes(index)"
              :aria-controls="`module-content-${index}`"
              @click="toggleModule(index)"
            >
              <div class="module-title">
                <span class="module-number">模块 {{ index + 1 }}</span>
                <h3>{{ module.title }}</h3>
              </div>
              <span class="module-toggle">{{ expandedModules.includes(index) ? '−' : '+' }}</span>
            </button>
            <div :id="`module-content-${index}`" class="module-content" v-show="expandedModules.includes(index)">
              <p class="module-desc">{{ module.description }}</p>
              <ul class="lesson-list">
                <li v-for="(lesson, lIndex) in module.lessons" :key="lIndex">
                  <IconMark class="lesson-icon" name="book" />
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
        <h2>这条路径适合谁？</h2>
        <div class="audience-grid">
          <div class="audience-card">
            <IconMark class="audience-icon" name="growth" />
            <h3>自我探索者</h3>
            <p>想理解自己的个人属性，不满足于“更好的自己”模板</p>
          </div>
          <div class="audience-card">
            <IconMark class="audience-icon" name="education" />
            <h3>心理学爱好者</h3>
            <p>愿意把玄学、心理学和哲学放在同一张桌面上对话</p>
          </div>
          <div class="audience-card">
            <IconMark class="audience-icon" name="career" />
            <h3>职业发展者</h3>
            <p>正在做职业、关系或人生方向选择，希望少一点社会化审判</p>
          </div>
          <div class="audience-card">
            <IconMark class="audience-icon" name="group" />
            <h3>关系经营者</h3>
            <p>想要理解关系模式，改善亲密关系、家庭关系或职场关系</p>
          </div>
          <div class="audience-card">
            <IconMark class="audience-icon" name="compass" />
            <h3>传统文化爱好者</h3>
            <p>对八字、紫微等传统文化感兴趣，希望系统化学习并应用于现代生活</p>
          </div>
          <div class="audience-card">
            <IconMark class="audience-icon" name="arrow" />
            <h3>未来从业者</h3>
            <p>计划从事个人成长、咨询相关领域，需要掌握专业工具和方法论</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 课程特色 -->
    <section class="course-features">
      <div class="container">
        <h2>共鉴的四个坚持</h2>
        <div class="features-grid">
          <div class="feature-item">
            <IconMark class="feature-icon" name="self" />
            <h3>理论与现实相接</h3>
            <p>每个概念都回到真实处境，用决策日志和小行动检验它是否真的有用。</p>
          </div>
          <div class="feature-item">
            <IconMark class="feature-icon" name="bridge" />
            <h3>多种语言互译</h3>
            <p>玄学负责看见属性，心理学负责处理旧循环，哲学负责提供人生脉络。</p>
          </div>
          <div class="feature-item">
            <IconMark class="feature-icon" name="refresh" />
            <h3>长期人本社群</h3>
            <p>不靠焦虑和排名驱动，靠真实记录、趣味练习和彼此照见保持连接。</p>
          </div>
          <div class="feature-item">
            <IconMark class="feature-icon" name="book" />
            <h3>把主动权留给人</h3>
            <p>不点评命盘层次、财富等级和能力高低，不预测具体因果，只帮助你更有依据地行动。</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 价格与报名 -->
    <section class="course-pricing">
      <div class="container">
        <h2>共鉴方式</h2>
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
            <button type="button" class="btn-enroll">立即报名</button>
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
            <button type="button" class="btn-enroll primary">立即报名</button>
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
            <button type="button" class="btn-enroll">立即报名</button>
          </div>
        </div>

        <div class="enrollment-notice">
          <p>具体开放时间与共鉴名额，以辰鉴最新通知为准</p>
          <p>参与咨询请联系：hello@chenjian.me</p>
        </div>
      </div>
    </section>

    <BrandFooter />
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
          title: '第一篇：见自己与时间坐标',
          description: '理解辰鉴的三层地图：先天属性、后天环境与主动选择',
          lessons: [
            '见自己：把个人属性从社会评价中分离出来',
            '知其序：理解阶段、时机与环境的变化',
            '哲学、心理学与玄学如何彼此翻译',
            '如何有边界地使用传统观察工具'
          ]
        },
        {
          title: '第二篇：性格密码与能量通路',
          description: '从八字结构进入天赋、弱点与充放电方式',
          lessons: [
            '时间坐标：如何读懂你的先天结构',
            '十神系统：把抽象配置翻译成心理动力',
            '能量通路：什么事情充电，什么事情耗电',
            '天赋与暗面天赋：用对与用错的区别',
            '案例实战：从属性到环境的翻译练习'
          ]
        },
        {
          title: '第三篇：关系模式与人生重复题',
          description: '用关系与潜意识视角，看见反复出现的互动脚本',
          lessons: [
            '关系模式：亲密关系、家庭与职场中的我',
            '核心矛盾：在想要与恐惧之间如何摆动',
            '内在小孩：旧经验正在保护什么',
            '人生谎言：哪些信念让你重复卡住',
            '案例实战：把旧循环改写成新答案'
          ]
        },
        {
          title: '第四篇：从说明书到行动',
          description: '把 fi 端的理解转译为 te 端可执行的生活选择',
          lessons: [
            '从命理到心理：个人属性的当代翻译',
            '最小可行行动：下周就能做的三件事',
            '用舍由时：顺环境，不顺从恐惧',
            '复盘与行为实验：为自己留下证据',
            '成长路径规划：未来 6—12 个月的能力建设'
          ]
        },
        {
          title: '第五篇：把建议还给具体的人',
          description: '练习不审判地回应真实的就业、关系与成长困境',
          lessons: [
            '就业选择：肯定能力，再看环境适配',
            '亲密关系：在关系中保留主体性',
            '家庭议题：把责任与自我价值分开',
            '青少年困惑：允许思考，也看见阶段任务',
            '综合案例：从说明书到行动端的交付流程'
          ]
        },
        {
          title: '第六篇：成为自己的长期观察者',
          description: '建立可持续的记录、日历、社群与复盘习惯',
          lessons: [
            '如何为自己做定期复盘',
            '决策日历：识别推进、等待与修整窗口',
            '行动方案制定：从认知到改变',
            '持续学习：建立你的个人知识系统',
            '共鉴实践：在社群里彼此照见'
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

/* 页面标题 */
.page-header {
  padding: 140px 20px 80px;
  background: linear-gradient(135deg, rgba(255, 240, 223, .85) 0%, rgba(184, 92, 80, .22) 100%);
  text-align: center;
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: var(--ink, #2f241b);
  margin-bottom: 20px;
}

.page-header p {
  font-size: 18px;
  color: var(--muted, #7d6653);
  line-height: 1.8;
}

/* 容器 */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
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
  color: var(--ink, #2f241b);
  margin-bottom: 20px;
}

.intro-text p {
  font-size: 16px;
  line-height: 1.8;
  color: var(--muted, #7d6653);
  margin-bottom: 15px;
}

.intro-benefits {
  margin-top: 30px;
}

.intro-benefits li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 16px;
  line-height: 2.2;
  color: var(--muted, #7d6653);
}

.intro-benefits .icon-mark {
  width: 19px;
  height: 19px;
  margin-top: 7px;
  flex: 0 0 auto;
  color: var(--cinnabar-deep, #9e3f35);
}

.course-card-preview {
  background: linear-gradient(135deg, rgba(255, 240, 223, .78) 0%, rgba(184, 92, 80, .12) 100%);
  padding: 40px;
  border-radius: 20px;
  border: 2px solid var(--cinnabar, #b85c50);
  position: relative;
}

.preview-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: var(--cinnabar, #b85c50);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.course-card-preview h3 {
  font-size: 28px;
  font-weight: 700;
  color: var(--ink, #2f241b);
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
  color: var(--cinnabar-deep, #9e3f35);
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--muted, #7d6653);
}

/* 课程大纲 */
.course-outline {
  padding: 80px 0;
  background: var(--surface-strong, #fffaf0);
}

.course-outline h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: var(--ink, #2f241b);
  margin-bottom: 15px;
}

.section-desc {
  text-align: center;
  color: var(--muted, #7d6653);
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
  border: 2px solid rgba(139, 90, 20, .16);
  transition: border-color var(--motion-standard, 220ms) var(--ease-out, ease);
}

.module-item:hover {
  border-color: var(--cinnabar, #b85c50);
}

.module-header {
  padding: 25px 30px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease);
}

.module-header:hover {
  background: var(--surface-strong, #fffaf0);
}

.module-title {
  display: flex;
  align-items: center;
  gap: 15px;
}

.module-number {
  background: var(--cinnabar, #b85c50);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.module-title h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--ink, #2f241b);
}

.module-toggle {
  font-size: 28px;
  color: var(--cinnabar-deep, #9e3f35);
  font-weight: 300;
}

.module-content {
  padding: 0 30px 25px;
  border-top: 1px solid var(--line, rgba(139, 90, 20, .16));
}

.module-desc {
  font-size: 15px;
  color: var(--muted, #7d6653);
  margin: 20px 0;
  line-height: 1.6;
}

.lesson-list li {
  padding: 12px 0;
  border-bottom: 1px solid var(--line, rgba(139, 90, 20, .16));
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: var(--muted, #7d6653);
}

.lesson-list li:last-child {
  border-bottom: none;
}

.lesson-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  color: var(--cinnabar-deep, #9e3f35);
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
  color: var(--ink, #2f241b);
  margin-bottom: 50px;
}

.audience-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
}

.audience-card {
  background: var(--surface-strong, #fffaf0);
  padding: 30px;
  border-radius: 15px;
  text-align: center;
  transition: box-shadow var(--motion-standard, 220ms) var(--ease-out, ease);
}

.audience-card:hover {
  transform: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.audience-icon {
  width: 42px;
  height: 42px;
  margin-bottom: 20px;
  color: var(--cinnabar-deep, #9e3f35);
}

.audience-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--ink, #2f241b);
  margin-bottom: 15px;
}

.audience-card p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--muted, #7d6653);
}

/* 课程特色 */
.course-features {
  padding: 80px 0;
  background: var(--surface-strong, #fffaf0);
}

.course-features h2 {
  font-size: 42px;
  font-weight: 700;
  text-align: center;
  color: var(--ink, #2f241b);
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
  width: 46px;
  height: 46px;
  margin-bottom: 20px;
  color: var(--cinnabar-deep, #9e3f35);
}

.feature-item h3 {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink, #2f241b);
  margin-bottom: 15px;
}

.feature-item p {
  font-size: 15px;
  line-height: 1.7;
  color: var(--muted, #7d6653);
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
  color: var(--ink, #2f241b);
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
  background: var(--surface-strong, #fffaf0);
  border-radius: 20px;
  padding: 40px;
  position: relative;
  transition: border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), background var(--motion-standard, 220ms) var(--ease-out, ease);
  border: 2px solid transparent;
}

.pricing-card:hover {
  transform: none;
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.1);
  border-color: var(--cinnabar, #b85c50);
}

.pricing-card.featured {
  background: linear-gradient(135deg, rgba(255, 240, 223, .78) 0%, rgba(184, 92, 80, .12) 100%);
  border-color: var(--cinnabar, #b85c50);
}

.pricing-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: var(--muted, #7d6653);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.pricing-badge.recommended {
  background: var(--cinnabar, #b85c50);
}

.pricing-card h3 {
  font-size: 24px;
  font-weight: 600;
  color: var(--ink, #2f241b);
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
  color: var(--cinnabar-deep, #9e3f35);
}

.price-original {
  font-size: 18px;
  color: var(--muted, #7d6653);
  text-decoration: line-through;
  margin-left: 10px;
}

.pricing-includes {
  margin-bottom: 30px;
}

.pricing-includes li {
  font-size: 15px;
  color: var(--muted, #7d6653);
  line-height: 2;
  padding-left: 20px;
  position: relative;
}

.pricing-includes li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--cinnabar-deep, #9e3f35);
  font-weight: 600;
}

.btn-enroll {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  color: var(--cinnabar, #b85c50);
  border: 2px solid var(--cinnabar, #b85c50);
  border-radius: 50px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.btn-enroll:hover {
  background: var(--cinnabar, #b85c50);
  color: #fff;
}

.btn-enroll.primary {
  background: var(--cinnabar, #b85c50);
  color: #fff;
}

.btn-enroll.primary:hover {
  background: var(--cinnabar-deep, #9e3f35);
}

.enrollment-notice {
  text-align: center;
  margin-top: 40px;
}

.enrollment-notice p {
  font-size: 15px;
  color: var(--muted, #7d6653);
  margin-bottom: 10px;
}

/* 页脚 */
.footer {
  background: var(--ink, #2f241b);
  padding: 40px 0;
  text-align: center;
  color: rgba(255, 250, 240, .76);
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    padding: 56px 20px 42px;
  }

  .page-header h1 {
    max-width: 100%;
    font-size: clamp(32px, 10vw, 44px);
    line-height: 1.15;
    overflow-wrap: anywhere;
  }

  .page-header p {
    font-size: 16px;
    line-height: 1.75;
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
    font-size: clamp(28px, 8vw, 34px);
  }

  .audience-grid,
  .pricing-cards {
    grid-template-columns: 1fr;
  }

  .module-header {
    min-height: 64px;
    align-items: flex-start;
    gap: 12px;
    padding: 18px 16px;
  }

  .module-title {
    min-width: 0;
    align-items: flex-start;
    gap: 9px;
  }

  .module-number {
    flex: 0 0 auto;
    padding: 6px 10px;
    font-size: 11px;
  }

  .module-title h3 {
    min-width: 0;
    font-size: 16px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .module-toggle {
    flex: 0 0 auto;
    font-size: 24px;
    line-height: 1.1;
  }

  .module-content {
    padding: 0 16px 20px;
  }

  .course-card-preview,
  .pricing-card,
  .audience-card {
    padding: 24px 20px;
  }

  .preview-badge {
    top: 14px;
    right: 14px;
    padding: 5px 10px;
    font-size: 11px;
  }

  .course-card-preview h3 {
    margin-bottom: 24px;
    font-size: 25px;
  }

  .preview-stats {
    gap: 10px;
  }

  .stat-number {
    font-size: 26px;
  }

  .stat-label {
    font-size: 12px;
  }

  .lesson-list li {
    align-items: flex-start;
    line-height: 1.6;
  }

  .lesson-icon {
    flex: 0 0 auto;
  }

  .btn-enroll {
    min-height: 48px;
  }
}

/* 课程页与主站保持同一套编辑感纸张主题。 */
.course {
  min-height: 100dvh;
  background: transparent;
}

.course .page-header {
  position: relative;
  overflow: hidden;
  padding: 62px 0 48px;
  background:
    linear-gradient(105deg, rgba(255, 250, 240, 0.9), rgba(255, 239, 222, 0.72)),
    radial-gradient(circle at 86% 20%, rgba(111, 159, 147, 0.18), transparent 25%),
    var(--paper-deep, #ead9bf);
}

.course .page-header::after {
  content: "共鉴";
  position: absolute;
  right: 8%;
  bottom: -30px;
  color: rgba(184, 92, 80, 0.08);
  font-family: var(--font-display, serif);
  font-size: 120px;
  font-weight: 900;
  line-height: 1;
  pointer-events: none;
}

.course .page-header .container {
  position: relative;
  z-index: 1;
}

.course-intro,
.target-audience,
.course-pricing {
  background: transparent;
}

.course-outline,
.course-features {
  background: rgba(255, 252, 245, 0.34);
}

.course-card-preview,
.module-item,
.audience-card,
.pricing-card {
  border-color: rgba(139, 90, 20, 0.14);
  background: rgba(255, 252, 245, 0.76);
  box-shadow: var(--shadow-card, 0 16px 48px -34px rgba(84, 48, 25, 0.48));
}

.course-card-preview,
.pricing-card.featured {
  border-color: rgba(184, 92, 80, 0.34);
  background: linear-gradient(145deg, rgba(255, 252, 245, 0.96), rgba(255, 239, 222, 0.82));
}

.course-card-preview h3,
.module-title h3,
.audience-card h3,
.pricing-card h3 {
  font-family: var(--font-display, serif);
}

.module-number,
.pricing-badge.recommended,
.btn-enroll.primary {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
}

.preview-badge {
  background: var(--cinnabar-deep, #9e3f35);
}

/* 移动端最终密度：课程内容以短段落和可展开模块为主，避免首屏过高。 */
@media (max-width: 768px) {
  .course .page-header {
    padding: 38px 0 30px;
  }

  .course .page-header::after {
    right: 4%;
    bottom: -18px;
    font-size: 72px;
  }

  .course .page-header h1 {
    font-size: clamp(32px, 10vw, 44px);
    line-height: 1.1;
  }

  .course-intro,
  .course-outline,
  .target-audience,
  .course-features,
  .course-pricing {
    padding-top: 40px;
    padding-bottom: 40px;
  }

  .intro-content {
    gap: 16px;
  }

  .intro-text h2,
  .course-outline h2,
  .target-audience h2,
  .course-features h2,
  .course-pricing h2 {
    margin-bottom: 22px;
    font-size: clamp(24px, 8vw, 30px);
    line-height: 1.25;
  }

  .intro-benefits {
    margin-top: 18px;
  }

  .intro-benefits li {
    gap: 8px;
    font-size: 16px;
    line-height: 1.75;
  }

  .course-card-preview,
  .pricing-card,
  .audience-card {
    padding: 16px;
    border-radius: 14px;
  }

  .course-card-preview h3 {
    margin-bottom: 18px;
    font-size: 22px;
  }

  .preview-stats {
    gap: 8px;
  }

  .stat-number {
    font-size: 24px;
  }

  .modules {
    width: 100%;
  }

  .module-item {
    margin-bottom: 12px;
    border-radius: 12px;
  }

  .module-header {
    min-height: 56px;
    gap: 8px;
    padding: 14px 12px;
  }

  .module-title {
    gap: 7px;
  }

  .module-number {
    padding: 5px 8px;
    font-size: 10px;
  }

  .module-title h3 {
    font-size: 15px;
    line-height: 1.4;
  }

  .module-toggle {
    min-width: 44px;
    min-height: 44px;
    font-size: 21px;
  }

  .module-content {
    padding: 0 12px 16px;
  }

  .module-desc {
    margin: 14px 0;
    font-size: 16px;
    line-height: 1.7;
  }

  .lesson-list li {
    gap: 9px;
    padding: 10px 0;
    font-size: 16px;
  }

  .audience-grid,
  .pricing-cards,
  .features-grid {
    gap: 12px;
  }

  .audience-icon,
  .feature-icon {
    width: 34px;
    height: 34px;
    margin-bottom: 12px;
  }

  .audience-card h3,
  .feature-item h3,
  .pricing-card h3 {
    margin-bottom: 10px;
    font-size: 19px;
  }

  .audience-card p,
  .feature-item p {
    font-size: 16px;
  }

  .pricing-card {
    padding-top: 20px;
  }

  .pricing-badge {
    top: 12px;
    right: 12px;
    padding: 5px 10px;
    font-size: 11px;
  }

  .btn-enroll {
    min-height: 46px;
  }
}

/* 按钮专项：报名按钮与全站 CTA 对齐，胶囊形状只留给标签。 */
.module-header {
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.btn-enroll {
  display: inline-flex;
  min-height: var(--button-height, 46px);
  align-items: center;
  justify-content: center;
  border: 1px solid var(--cinnabar, #b85c50);
  border-radius: var(--button-radius, 13px);
  padding: 0 18px;
  color: var(--cinnabar-deep, #9e3f35);
  font-family: var(--font-ui, sans-serif);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.btn-enroll:hover {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: rgba(184, 92, 80, 0.1);
  color: var(--cinnabar-deep, #9e3f35);
  transform: none;
}

.btn-enroll:active {
  transform: scale(0.985);
}

.btn-enroll.primary {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  color: #fffaf0;
}

.btn-enroll.primary:hover {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), #8f352f);
  color: #fffaf0;
}
</style>
