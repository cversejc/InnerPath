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
        <!-- AI 生成的完整内容（优先展示） -->
        <div v-if="report && report.aiGeneratedContent" class="ai-content">
          <div class="content-card">
            <div class="ai-badge">
              <span class="badge-icon">✨</span>
              <span>AI 深度分析</span>
            </div>

            <!-- 命理基础（特殊展示） -->
            <div v-if="foundationData" class="foundation-section">
              <h2 class="section-title">
                <span class="title-icon">🔮</span>
                命理基础
              </h2>

              <!-- 八字四柱 -->
              <div v-if="foundationData.bazi" class="bazi-container">
                <h3 class="subsection-title">八字四柱</h3>
                <div class="pillar-grid">
                  <div v-if="foundationData.bazi.year" class="pillar-card">
                    <div class="pillar-label">年柱</div>
                    <div class="pillar-value">{{ foundationData.bazi.year.stem }}{{ foundationData.bazi.year.branch }}</div>
                    <div v-if="foundationData.bazi.year.ten_god" class="pillar-god">{{ foundationData.bazi.year.ten_god }}</div>
                  </div>
                  <div v-if="foundationData.bazi.month" class="pillar-card">
                    <div class="pillar-label">月柱</div>
                    <div class="pillar-value">{{ foundationData.bazi.month.stem }}{{ foundationData.bazi.month.branch }}</div>
                    <div v-if="foundationData.bazi.month.ten_god" class="pillar-god">{{ foundationData.bazi.month.ten_god }}</div>
                  </div>
                  <div v-if="foundationData.bazi.day" class="pillar-card day-pillar">
                    <div class="pillar-label">日柱（日主）</div>
                    <div class="pillar-value">{{ foundationData.bazi.day.stem }}{{ foundationData.bazi.day.branch }}</div>
                  </div>
                  <div v-if="foundationData.bazi.hour" class="pillar-card">
                    <div class="pillar-label">时柱</div>
                    <div class="pillar-value">{{ foundationData.bazi.hour.stem }}{{ foundationData.bazi.hour.branch }}</div>
                    <div v-if="foundationData.bazi.hour.ten_god" class="pillar-god">{{ foundationData.bazi.hour.ten_god }}</div>
                  </div>
                </div>
              </div>

              <!-- 紫微斗数 -->
              <div v-if="foundationData.ziwei" class="ziwei-container">
                <h3 class="subsection-title">紫微斗数</h3>
                <div class="palace-grid">
                  <div v-if="foundationData.ziwei.life_palace" class="palace-card">
                    <div class="palace-label">命宫</div>
                    <div class="palace-stars">
                      <span v-for="(star, idx) in foundationData.ziwei.life_palace.main_stars" :key="idx" class="star-tag main">{{ star }}</span>
                      <span v-for="(star, idx) in foundationData.ziwei.life_palace.aux_stars" :key="'aux-' + idx" class="star-tag aux">{{ star }}</span>
                    </div>
                  </div>
                  <div v-if="foundationData.ziwei.career_palace" class="palace-card">
                    <div class="palace-label">事业宫</div>
                    <div class="palace-stars">
                      <span v-for="(star, idx) in foundationData.ziwei.career_palace.main_stars" :key="idx" class="star-tag main">{{ star }}</span>
                    </div>
                  </div>
                  <div v-if="foundationData.ziwei.wealth_palace" class="palace-card">
                    <div class="palace-label">财帛宫</div>
                    <div class="palace-stars">
                      <span v-for="(star, idx) in foundationData.ziwei.wealth_palace.main_stars" :key="idx" class="star-tag main">{{ star }}</span>
                    </div>
                  </div>
                  <div v-if="foundationData.ziwei.relationship_palace" class="palace-card">
                    <div class="palace-label">夫妻宫</div>
                    <div class="palace-stars">
                      <span v-for="(star, idx) in foundationData.ziwei.relationship_palace.main_stars" :key="idx" class="star-tag main">{{ star }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="foundationData.ziwei.patterns && foundationData.ziwei.patterns.length > 0" class="patterns-section">
                  <div class="pattern-label">关键格局：</div>
                  <div class="pattern-tags">
                    <span v-for="(pattern, idx) in foundationData.ziwei.patterns" :key="idx" class="pattern-tag">{{ pattern }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 其他内容 -->
            <div class="markdown-content" v-html="formatMarkdown(contentWithoutFoundation)"></div>
          </div>
        </div>

        <!-- 结构化内容展示（降级方案） -->
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
      report: null,
      foundationData: null,
      contentWithoutFoundation: ''
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

        // 解析命理基础数据
        if (this.report.aiGeneratedContent) {
          this.parseFoundationData(this.report.aiGeneratedContent)
        }
      } else {
        // 如果没有找到报告，显示示例报告
        console.warn('Report not found, showing example')
        this.report = this.getExampleReport()
      }
    },
    normalizeReportData(report) {
      // 标准化数据结构，处理可能的字段名差异
      const normalized = {
        basicInfo: report.basicInfo || report.basic_info || {
          name: '用户',
          reportDate: new Date().toISOString().split('T')[0]
        },
        structuredSections: report.structuredSections || report.structured_sections || null,
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

      // Debug: 打印 structuredSections 的内容
      console.log('structuredSections 内容:', normalized.structuredSections)
      if (normalized.structuredSections) {
        console.log('structuredSections keys:', Object.keys(normalized.structuredSections))
        console.log('energy:', normalized.structuredSections.energy)
        console.log('topics:', normalized.structuredSections.topics)
        console.log('summary:', normalized.structuredSections.summary)
      }

      // Debug: 打印 aiGeneratedContent
      console.log('aiGeneratedContent 存在吗?', !!normalized.aiGeneratedContent)
      console.log('aiGeneratedContent 长度:', normalized.aiGeneratedContent?.length)
      if (normalized.aiGeneratedContent) {
        console.log('aiGeneratedContent 预览:', normalized.aiGeneratedContent.substring(0, 200))
      }

      return normalized
    },
    parseFoundationData(content) {
      // 尝试从内容中提取命理基础的JSON数据
      // 后端在 _format_foundation_as_markdown 中会输出结构化的Markdown
      // 我们需要解析这些内容

      // 提取八字四柱
      const baziMatch = content.match(/### 八字四柱\s+([\s\S]*?)(?=###|$)/i)
      if (baziMatch) {
        const baziText = baziMatch[1]
        const bazi = {}

        // 解析年柱
        const yearMatch = baziText.match(/\*\*年柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/)
        if (yearMatch) {
          const [stem, branch] = this.splitStemBranch(yearMatch[1])
          bazi.year = { stem, branch, ten_god: yearMatch[2] || '' }
        }

        // 解析月柱
        const monthMatch = baziText.match(/\*\*月柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/)
        if (monthMatch) {
          const [stem, branch] = this.splitStemBranch(monthMatch[1])
          bazi.month = { stem, branch, ten_god: monthMatch[2] || '' }
        }

        // 解析日柱
        const dayMatch = baziText.match(/\*\*日柱[^：]*：\*\*\s*([^\s（]+)/)
        if (dayMatch) {
          const [stem, branch] = this.splitStemBranch(dayMatch[1])
          bazi.day = { stem, branch }
        }

        // 解析时柱
        const hourMatch = baziText.match(/\*\*时柱：\*\*\s*([^\s（]+)(?:（([^）]+)）)?/)
        if (hourMatch) {
          const [stem, branch] = this.splitStemBranch(hourMatch[1])
          bazi.hour = { stem, branch, ten_god: hourMatch[2] || '' }
        }

        if (Object.keys(bazi).length > 0) {
          this.foundationData = this.foundationData || {}
          this.foundationData.bazi = bazi
        }
      }

      // 提取紫微斗数
      const ziweiMatch = content.match(/### 紫微斗数\s+([\s\S]*?)(?=##[^#]|$)/i)
      if (ziweiMatch) {
        const ziweiText = ziweiMatch[1]
        const ziwei = {}

        // 解析命宫 - 格式: **命宫：** 主星名称
        const lifePalaceMatch = ziweiText.match(/\*\*命宫：\*\*\s*([^\n]+)/)
        if (lifePalaceMatch) {
          ziwei.life_palace = {
            main_stars: lifePalaceMatch[1].split('、').filter(s => s.trim()),
            aux_stars: []
          }
          // 查找辅星 - 格式: - 辅星：星名
          const auxStarsMatch = ziweiText.match(/\-\s*辅星：([^\n]+)/)
          if (auxStarsMatch) {
            ziwei.life_palace.aux_stars = auxStarsMatch[1].split('、').filter(s => s.trim())
          }
        }

        // 解析事业宫 - 格式: **事业宫：** 主星名称
        const careerMatch = ziweiText.match(/\*\*事业宫：\*\*\s*([^\n]+)/)
        if (careerMatch) {
          ziwei.career_palace = {
            main_stars: careerMatch[1].split('、').filter(s => s.trim())
          }
        }

        // 解析财帛宫 - 格式: **财帛宫：** 主星名称
        const wealthMatch = ziweiText.match(/\*\*财帛宫：\*\*\s*([^\n]+)/)
        if (wealthMatch) {
          ziwei.wealth_palace = {
            main_stars: wealthMatch[1].split('、').filter(s => s.trim())
          }
        }

        // 解析夫妻宫 - 格式: **夫妻宫：** 主星名称
        const relationshipMatch = ziweiText.match(/\*\*夫妻宫：\*\*\s*([^\n]+)/)
        if (relationshipMatch) {
          ziwei.relationship_palace = {
            main_stars: relationshipMatch[1].split('、').filter(s => s.trim())
          }
        }

        // 解析格局 - 格式: **格局：** 格局名称
        const patternsMatch = ziweiText.match(/\*\*格局：\*\*\s*([^\n]+)/)
        if (patternsMatch) {
          ziwei.patterns = patternsMatch[1].split('、').filter(s => s.trim())
        }

        if (Object.keys(ziwei).length > 0) {
          this.foundationData = this.foundationData || {}
          this.foundationData.ziwei = ziwei
        }
      }

      // 移除命理基础部分，保留其他内容
      if (baziMatch || ziweiMatch) {
        // 更精确的正则：匹配 "## 命理基础" 到下一个 "## " 之间的所有内容
        this.contentWithoutFoundation = content.replace(/## 命理基础[\s\S]*?(?=\n## (?!#)|\n---\n|\n\n## (?!#)|$)/i, '')
      } else {
        this.contentWithoutFoundation = content
      }

      console.log('Foundation data parsed:', this.foundationData)
      console.log('Content without foundation length:', this.contentWithoutFoundation.length)
    },
    splitStemBranch(text) {
      // 天干地支各一个字
      if (text.length >= 2) {
        return [text[0], text[1]]
      }
      return [text, '']
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

      // 章节图标映射
      const sectionIcons = {
        '能量特质': '⚡',
        '能量内核': '⚡',
        '人生主题': '🎭',
        '职业': '💼',
        '关系': '💕',
        '个人成长': '🌱',
        '压力': '🧘',
        '家庭': '🏠',
        '总结': '🌟'
      }

      // 为二级标题添加图标
      let html = content
      Object.keys(sectionIcons).forEach(keyword => {
        const icon = sectionIcons[keyword]
        const regex = new RegExp(`^## ([^#]*${keyword}[^\\n]*)$`, 'gim')
        html = html.replace(regex, `<h2><span class="section-icon">${icon}</span> $1</h2>`)
      })

      // 简单的 Markdown 转 HTML
      html = html
        // 分割线
        .replace(/^---$/gim, '<hr>')
        // 标题（从高级到低级，避免误匹配）
        .replace(/^##### (.*$)/gim, '<h5>$1</h5>')
        .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        // 粗体
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // 列表项
        .replace(/^\- (.*$)/gim, '<li>$1</li>')
        .replace(/^\* (.*$)/gim, '<li>$1</li>')
        // 段落：两个换行符表示段落分隔
        .replace(/\n\n+/g, '</p><p>')
        // 单个换行符保留为换行
        .replace(/\n/g, '<br>')

      // 包裹列表项
      html = html.replace(/(<li>.*?<\/li>(<br>)?)+/g, (match) => {
        return '<ul>' + match.replace(/<br>/g, '') + '</ul>'
      })

      // 包裹段落
      if (!html.startsWith('<h') && !html.startsWith('<ul>')) {
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
  padding: 40px;
  margin-bottom: 30px;
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
  line-height: 2;
  color: #555;
}

.markdown-content h2 {
  font-size: 22px;
  margin-top: 50px;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
  color: #2d3436;
  display: flex;
  align-items: center;
  gap: 10px;
}

.markdown-content h2:first-child {
  margin-top: 0;
}

.markdown-content h3 {
  font-size: 18px;
  margin-top: 35px;
  margin-bottom: 18px;
  color: #d4524f;
  font-weight: 600;
}

.markdown-content h4 {
  font-size: 16px;
  margin-top: 28px;
  margin-bottom: 15px;
  color: #555;
  font-weight: 600;
}

.markdown-content h5 {
  font-size: 15px;
  margin-top: 22px;
  margin-bottom: 12px;
  color: #666;
  font-weight: 600;
}

.markdown-content p {
  margin-bottom: 20px;
  text-align: justify;
}

.markdown-content hr {
  border: none;
  height: 3px;
  background: linear-gradient(to right, transparent, #d4524f, transparent);
  margin: 45px 0;
  position: relative;
}

.markdown-content hr::before {
  content: '✦';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: #fff;
  color: #d4524f;
  padding: 0 15px;
  font-size: 16px;
}

.markdown-content ul {
  margin: 20px 0;
  padding-left: 0;
}

.markdown-content li {
  margin-bottom: 12px;
  padding-left: 25px;
  position: relative;
  line-height: 2;
}

.markdown-content li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: #d4524f;
  font-weight: 600;
  font-size: 18px;
}

.markdown-content strong {
  color: #2d3436;
  font-weight: 600;
}

.section-icon {
  font-size: 24px;
}

/* 命理基础样式 */
.foundation-section {
  margin-bottom: 35px;
  padding-bottom: 25px;
  border-bottom: 2px solid #f0f0f0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: #2d3436;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.title-icon {
  font-size: 28px;
}

.subsection-title {
  font-size: 17px;
  font-weight: 600;
  color: #d4524f;
  margin: 20px 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subsection-title::before {
  content: '◆';
  font-size: 14px;
  color: #d4524f;
}

/* 八字四柱 */
.bazi-container {
  margin-bottom: 30px;
}

.pillar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.pillar-card {
  background: linear-gradient(135deg, #fff9f9 0%, #fff5f5 100%);
  border: 1px solid #f0d0d0;
  border-radius: 10px;
  padding: 18px;
  text-align: center;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.pillar-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(135deg, #d4524f 0%, #e74c3c 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.pillar-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(212, 82, 79, 0.15);
  border-color: #d4524f;
}

.pillar-card:hover::before {
  opacity: 1;
}

.pillar-card.day-pillar {
  background: linear-gradient(135deg, #d4524f 0%, #e74c3c 100%);
  border-color: #d4524f;
  box-shadow: 0 4px 12px rgba(212, 82, 79, 0.3);
}

.pillar-card.day-pillar::before {
  opacity: 0;
}

.pillar-card.day-pillar:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 20px rgba(212, 82, 79, 0.4);
}

.pillar-card.day-pillar .pillar-label,
.pillar-card.day-pillar .pillar-value {
  color: #fff;
}

.pillar-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.pillar-card.day-pillar .pillar-label {
  color: rgba(255, 255, 255, 0.9);
}

.pillar-value {
  font-size: 26px;
  font-weight: 700;
  color: #d4524f;
  margin-bottom: 6px;
  letter-spacing: 3px;
}

.pillar-god {
  font-size: 11px;
  color: #666;
  background: rgba(255, 255, 255, 0.9);
  padding: 3px 9px;
  border-radius: 10px;
  display: inline-block;
  margin-top: 4px;
  border: 1px solid #f0d0d0;
}

/* 紫微斗数 */
.ziwei-container {
  margin-bottom: 0;
}

.palace-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.palace-card {
  background: linear-gradient(135deg, #fafbfc 0%, #f8f9fa 100%);
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  padding: 16px;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.palace-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.palace-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.15);
  border-color: #667eea;
}

.palace-card:hover::before {
  opacity: 1;
}

.palace-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 10px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.palace-stars {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.star-tag {
  padding: 5px 11px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.star-tag.main {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.3);
}

.star-tag.main:hover {
  transform: scale(1.05);
  box-shadow: 0 3px 8px rgba(102, 126, 234, 0.4);
}

.star-tag.aux {
  background: #f0f0f0;
  color: #666;
  border: 1px solid #e0e0e0;
}

.patterns-section {
  margin-top: 15px;
  padding: 14px;
  background: linear-gradient(135deg, #fff9f9 0%, #fff5f5 100%);
  border-radius: 8px;
  border-left: 3px solid #d4524f;
}

.pattern-label {
  font-size: 13px;
  color: #999;
  margin-bottom: 8px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.pattern-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pattern-tag {
  background: linear-gradient(135deg, #d4524f 0%, #e74c3c 100%);
  color: #fff;
  padding: 5px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(212, 82, 79, 0.3);
  transition: all 0.2s;
}

.pattern-tag:hover {
  transform: scale(1.05);
  box-shadow: 0 3px 8px rgba(212, 82, 79, 0.4);
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

/* 新增：结构化章节样式 */
.structured-sections {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  color: #333;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.title-icon {
  font-size: 28px;
}

/* 能量特质章节 */
.energy-section .subsections {
  display: grid;
  gap: 20px;
}

.subsection-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  padding: 25px;
  border-radius: 12px;
  border-left: 4px solid #d4524f;
  transition: transform 0.2s, box-shadow 0.2s;
}

.subsection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}

.subsection-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 15px;
}

.subsection-icon {
  font-size: 24px;
}

.subsection-header h3 {
  font-size: 18px;
  color: #d4524f;
  margin: 0;
}

.subsection-content {
  font-size: 15px;
  line-height: 1.8;
  color: #555;
  text-align: justify;
}

/* 议题章节 */
.topic-section {
  background: #ffffff;
  border: 1px solid #e8e8e8;
}

.topic-subsections {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.topic-subsection {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.topic-subsection-title {
  font-size: 16px;
  color: #d4524f;
  margin-bottom: 12px;
  font-weight: 600;
}

.topic-content {
  font-size: 15px;
  line-height: 1.8;
  color: #555;
  text-align: justify;
}

/* 行动清单 */
.action-checklist {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-item-check {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  transition: background 0.2s;
}

.action-item-check:hover {
  background: #fffbfb;
}

.action-item-check input[type="checkbox"] {
  margin-top: 4px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #d4524f;
}

.action-item-check label {
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
  color: #555;
  cursor: pointer;
}

.action-item-check input[type="checkbox"]:checked + label {
  text-decoration: line-through;
  color: #999;
}

/* 总结章节 */
.summary-section {
  background: linear-gradient(135deg, #fff5f5 0%, #ffe8e8 100%);
  border: 2px solid #d4524f;
}

.summary-highlight {
  background: #ffffff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #d4524f;
}

.summary-highlight h3 {
  font-size: 16px;
  color: #d4524f;
  margin-bottom: 10px;
}

.summary-highlight p {
  font-size: 15px;
  line-height: 1.8;
  color: #555;
  margin: 0;
}

.summary-message {
  background: rgba(255, 255, 255, 0.6);
  padding: 25px;
  border-radius: 8px;
  text-align: center;
}

.summary-message p {
  font-size: 16px;
  line-height: 2;
  color: #333;
  font-weight: 500;
  margin: 0;
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

  .pillar-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .palace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
