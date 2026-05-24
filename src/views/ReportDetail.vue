<template>
  <div class="report-detail">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="nav-container">
        <div class="logo">离火引</div>
        <ul class="nav-menu">
          <li><router-link to="/pages/home/home" class="nav-link">首页</router-link></li>
          <li><router-link to="/pages/user/user" class="nav-link">个人中心</router-link></li>
        </ul>
      </div>
    </nav>

    <!-- 报告头部 -->
    <section v-if="report" class="report-header">
      <div class="container">
        <button class="btn-back" @click="goBack">← 返回</button>
        <h1>个人能量地图报告</h1>
        <div class="report-meta">
          <span>生成日期：{{ report.basicInfo?.reportDate || '今天' }}</span>
          <span class="divider">|</span>
          <span>{{ report.basicInfo?.name || '用户' }}</span>
        </div>
      </div>
    </section>

    <!-- 加载中 -->
    <section v-else class="report-header">
      <div class="container">
        <h1>加载中...</h1>
      </div>
    </section>

    <!-- 报告内容 -->
    <section class="report-content">
      <div class="container">
        <!-- AI 生成的完整内容 -->
        <div v-if="report && report.aiGeneratedContent" class="ai-content">
          <div class="content-card">
            <div class="ai-badge">
              <span class="badge-icon">✨</span>
              <span>AI 深度分析</span>
            </div>
            <div class="markdown-content" v-html="formatMarkdown(report.aiGeneratedContent)"></div>
          </div>
        </div>

        <!-- 结构化内容展示 -->
        <div v-else-if="report" class="structured-content">
          <!-- 能量特质 -->
          <div class="content-card">
            <h2>一、能量特质分析</h2>
            <div class="energy-type">
              <span class="type-badge">{{ report.energyProfile?.type || '综合型' }}</span>
            </div>
            <div class="traits">
              <strong>核心特质：</strong>{{ report.energyProfile?.coreTraits || '独特的个人特质' }}
            </div>
            <p class="description">{{ report.energyProfile?.description || '' }}</p>
          </div>

          <!-- 职业发展 -->
          <div class="content-card">
            <h2>二、职业发展建议</h2>
            <div class="section-content">
              <h3>适合的职业路径</h3>
              <ul class="path-list">
                <li v-for="(path, index) in report.careerGuidance.suitablePaths" :key="index">
                  {{ path }}
                </li>
              </ul>
              <h3>工作风格</h3>
              <p>{{ report.careerGuidance.workStyle }}</p>
              <h3>发展建议</h3>
              <ul class="suggestion-list">
                <li v-for="(suggestion, index) in report.careerGuidance.developmentSuggestions" :key="index">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>

          <!-- 关系模式 -->
          <div class="content-card">
            <h2>三、关系模式解读</h2>
            <div class="section-content">
              <h3>关系风格</h3>
              <p>{{ report.relationshipPattern.style }}</p>
              <div class="two-columns">
                <div class="column">
                  <h3>优势</h3>
                  <ul class="trait-list">
                    <li v-for="(strength, index) in report.relationshipPattern.strengths" :key="index">
                      {{ strength }}
                    </li>
                  </ul>
                </div>
                <div class="column">
                  <h3>挑战</h3>
                  <ul class="trait-list">
                    <li v-for="(challenge, index) in report.relationshipPattern.challenges" :key="index">
                      {{ challenge }}
                    </li>
                  </ul>
                </div>
              </div>
              <h3>成长方向</h3>
              <p>{{ report.relationshipPattern.growthDirection }}</p>
            </div>
          </div>

          <!-- 行动方案 -->
          <div class="content-card">
            <h2>四、个性化行动方案</h2>
            <div class="action-plans">
              <div v-for="(plan, index) in report.personalGrowth.actionPlan" :key="index" class="action-item">
                <div class="action-header">
                  <span class="action-number">{{ index + 1 }}</span>
                  <h3>{{ plan.area }}</h3>
                </div>
                <p class="action-detail"><strong>具体行动：</strong>{{ plan.action }}</p>
                <p class="action-timeline"><strong>时间建议：</strong>{{ plan.timeline }}</p>
              </div>
            </div>
          </div>

          <!-- 总结 -->
          <div class="content-card summary-card">
            <h2>五、总结与寄语</h2>
            <p class="summary-text">{{ report.summary }}</p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="report-actions">
          <button class="btn-action" @click="downloadPDF">
            <span class="icon">📄</span>
            下载 PDF
          </button>
          <button class="btn-action" @click="shareReport">
            <span class="icon">🔗</span>
            分享报告
          </button>
          <button class="btn-action primary" @click="goToBooking">
            <span class="icon">💬</span>
            预约深度咨询
          </button>
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
  name: 'ReportDetail',
  data() {
    return {
      report: null
    }
  },
  mounted() {
    this.loadReport()
  },
  methods: {
    loadReport() {
      const reportId = this.$route.query.id
      console.log('Loading report with ID:', reportId)

      const reports = JSON.parse(localStorage.getItem('userReports') || '[]')
      console.log('All reports in localStorage:', reports)

      const reportData = reports.find(r => r.id == reportId)
      console.log('Found report data:', reportData)

      if (reportData && reportData.report) {
        // 确保数据结构正确
        this.report = this.normalizeReportData(reportData.report)
        console.log('Normalized report:', this.report)
      } else {
        // 如果没有找到报告，显示示例报告
        console.warn('Report not found, showing example')
        this.report = this.getExampleReport()
      }
    },
    normalizeReportData(report) {
      // 标准化数据结构，处理可能的字段名差异
      return {
        basicInfo: report.basicInfo || report.basic_info || {
          name: '用户',
          reportDate: new Date().toISOString().split('T')[0]
        },
        energyProfile: report.energyProfile || report.energy_profile || {
          type: '综合型',
          coreTraits: '独特的个人特质',
          description: '正在分析中...'
        },
        careerGuidance: report.careerGuidance || report.career_guidance || {
          suitablePaths: [],
          workStyle: '',
          developmentSuggestions: []
        },
        relationshipPattern: report.relationshipPattern || report.relationship_pattern || {
          style: '',
          strengths: [],
          challenges: [],
          growthDirection: ''
        },
        personalGrowth: report.personalGrowth || report.personal_growth || {
          actionPlan: []
        },
        summary: report.summary || '你是独特的个体，拥有无限的成长潜力。',
        aiGeneratedContent: report.aiGeneratedContent || report.ai_generated_content || report.ai_raw_content || null
      }
    },
    getExampleReport() {
      return {
        basicInfo: {
          name: '示例用户',
          reportDate: new Date().toISOString().split('T')[0]
        },
        energyProfile: {
          type: '生长驱动型',
          coreTraits: '创新求变、积极进取、富有创造力',
          description: '你的能量倾向于向外扩展和生长，喜欢探索新事物，具有强烈的成长动力。'
        },
        careerGuidance: {
          suitablePaths: ['创意型工作', '产品经理', '创业者'],
          workStyle: '你适合需要创新和开拓的工作环境',
          developmentSuggestions: ['持续学习新技能', '拓展人际网络', '发挥创新优势']
        },
        relationshipPattern: {
          style: '在关系中追求成长和新鲜感',
          strengths: ['积极主动', '富有活力', '能带动对方成长'],
          challenges: ['容易急躁', '缺乏耐心', '需要学习倾听'],
          growthDirection: '学习放慢节奏，给予对方更多耐心和关注'
        },
        personalGrowth: {
          actionPlan: [
            {
              area: '能量管理',
              action: '每天预留30分钟独处时间，进行自我觉察',
              timeline: '立即开始，持续21天'
            }
          ]
        },
        summary: '你是生长驱动型，具有创新求变、积极进取的特质。建议你从认识自己的能量模式开始，逐步建立适合自己的成长路径。',
        aiGeneratedContent: null
      }
    },
    formatMarkdown(content) {
      if (!content) return ''

      // 简单的 Markdown 转 HTML
      let html = content
        // 标题
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        // 粗体
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // 列表项
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/^\* (.*$)/gim, '<li>$1</li>')
        // 段落
        .replace(/\n\n/g, '</p><p>')

      // 包裹列表项
      html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')

      // 包裹段落
      if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>'
      }

      return html
    },
    goBack() {
      this.$router.go(-1)
    },
    downloadPDF() {
      alert('PDF 下载功能开发中...')
    },
    shareReport() {
      alert('分享功能开发中...')
    },
    goToBooking() {
      this.$router.push('/pages/booking/booking')
    }
  }
}
</script>

<style scoped>
.report-detail {
  width: 100%;
  background: #f8f9fa;
  min-height: 100vh;
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

.nav-link:hover {
  color: #d4524f;
}

/* 报告头部 */
.report-header {
  padding: 100px 20px 40px;
  background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
}

.btn-back {
  padding: 8px 16px;
  font-size: 14px;
  color: #666;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  margin-bottom: 20px;
  transition: all 0.3s;
}

.btn-back:hover {
  background: #fff;
  color: #d4524f;
}

.report-header h1 {
  font-size: 36px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 15px;
}

.report-meta {
  font-size: 15px;
  color: #636e72;
}

.divider {
  margin: 0 10px;
}

/* 容器 */
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 报告内容 */
.report-content {
  padding: 40px 0 80px;
}

.content-card {
  background: #fff;
  border-radius: 15px;
  padding: 35px;
  margin-bottom: 25px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.content-card h2 {
  font-size: 24px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.content-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2d3436;
  margin: 20px 0 12px;
}

/* AI 内容 */
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 25px;
}

.badge-icon {
  font-size: 16px;
}

.markdown-content {
  line-height: 1.8;
  color: #555;
}

.markdown-content h2 {
  font-size: 22px;
  margin-top: 30px;
  margin-bottom: 15px;
}

.markdown-content h3 {
  font-size: 18px;
  margin-top: 20px;
  margin-bottom: 10px;
}

.markdown-content p {
  margin-bottom: 15px;
}

.markdown-content li {
  margin-bottom: 8px;
  padding-left: 20px;
  position: relative;
}

.markdown-content li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

/* 能量类型 */
.energy-type {
  margin-bottom: 20px;
}

.type-badge {
  display: inline-block;
  background: linear-gradient(135deg, #d4524f 0%, #e74c3c 100%);
  color: #fff;
  padding: 10px 24px;
  border-radius: 25px;
  font-size: 18px;
  font-weight: 600;
}

.traits {
  font-size: 16px;
  color: #555;
  margin-bottom: 15px;
}

.traits strong {
  color: #2d3436;
}

.description {
  font-size: 15px;
  line-height: 1.8;
  color: #666;
}

/* 列表 */
.path-list,
.suggestion-list,
.trait-list {
  margin: 15px 0;
}

.path-list li,
.suggestion-list li,
.trait-list li {
  font-size: 15px;
  color: #555;
  line-height: 2;
  padding-left: 25px;
  position: relative;
}

.path-list li::before,
.suggestion-list li::before,
.trait-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
}

/* 两列布局 */
.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin: 20px 0;
}

/* 行动方案 */
.action-plans {
  display: grid;
  gap: 20px;
}

.action-item {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid #d4524f;
}

.action-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 15px;
}

.action-number {
  width: 32px;
  height: 32px;
  background: #d4524f;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
}

.action-item h3 {
  font-size: 18px;
  margin: 0;
}

.action-detail,
.action-timeline {
  font-size: 14px;
  color: #666;
  line-height: 1.8;
  margin-bottom: 8px;
}

/* 总结 */
.summary-card {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border: 2px solid #d4524f;
}

.summary-text {
  font-size: 16px;
  line-height: 2;
  color: #555;
  text-align: justify;
}

/* 操作按钮 */
.report-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 40px;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  font-size: 15px;
  font-weight: 600;
  color: #666;
  background: #fff;
  border: 2px solid #e0e0e0;
  border-radius: 50px;
  transition: all 0.3s;
}

.btn-action:hover {
  border-color: #d4524f;
  color: #d4524f;
  transform: translateY(-2px);
}

.btn-action.primary {
  background: #d4524f;
  color: #fff;
  border-color: #d4524f;
}

.btn-action.primary:hover {
  background: #c0392b;
  border-color: #c0392b;
}

.icon {
  font-size: 18px;
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

  .report-header {
    padding: 80px 20px 30px;
  }

  .report-header h1 {
    font-size: 28px;
  }

  .content-card {
    padding: 25px 20px;
  }

  .two-columns {
    grid-template-columns: 1fr;
  }

  .report-actions {
    flex-direction: column;
  }

  .btn-action {
    width: 100%;
    justify-content: center;
  }
}
</style>
