<template>
  <div class="report-detail">
    <BrandNav />

    <!-- 报告头部 -->
    <section v-if="report" class="report-header">
      <div class="container">
        <button class="btn-back" type="button" @click="goBack"><IconMark name="arrow-left" />返回</button>
        <h1>辰鉴·人生说明书</h1>
        <div class="report-meta">
          <span>生成日期：{{ report.basicInfo?.reportDate || '今天' }}</span>
          <span class="divider">|</span>
          <span>{{ report.basicInfo?.name || '用户' }}</span>
        </div>
      </div>
    </section>

    <!-- 打开报告时的状态 -->
    <section v-else-if="loading" class="report-header">
      <div class="container">
        <h1>正在打开你的个人报告…</h1>
      </div>
    </section>
    <section v-else class="report-header">
      <div class="container">
        <button class="btn-back" type="button" @click="goBack"><IconMark name="arrow-left" />返回</button>
        <h1>{{ loadError || '报告不存在或无权访问' }}</h1>
      </div>
    </section>

    <!-- 报告内容 -->
    <section class="report-content">
      <div class="container">
        <!-- AI 生成的完整内容（优先展示） -->
        <div v-if="report && report.aiGeneratedContent" class="ai-content">
          <div class="content-card">
            <div class="ai-badge">
              <IconMark class="badge-icon" name="spark" />
              <span>辰鉴结构化解读</span>
            </div>

            <!-- 命理基础（特殊展示） -->
            <div v-if="foundationData" class="foundation-section">
              <h2 class="section-title">
                <IconMark class="title-icon" name="compass" />
                先天坐标
              </h2>

              <!-- 八字四柱 -->
              <div v-if="foundationData.bazi" class="bazi-container">
                <h3 class="subsection-title">八字坐标</h3>
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
                <h3 class="subsection-title">紫微坐标</h3>
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
            <h2>一、我是谁 · 性格密码</h2>
            <div class="energy-type">
              <span class="type-badge">{{ report.energyProfile?.type || '综合型' }}</span>
            </div>
            <div class="traits">
              <strong>核心特质：</strong>{{ report.energyProfile?.coreTraits || '独特的个人特质' }}
            </div>
            <p class="description">{{ report.energyProfile?.description || '' }}</p>
          </div>

            <!-- 行动方向 -->
          <div class="content-card">
            <h2>二、我往哪去 · 环境与方向</h2>
            <div class="section-content">
              <h3>可以尝试的方向</h3>
              <ul class="path-list">
                <li v-for="(path, index) in report.careerGuidance.suitablePaths" :key="index">
                  {{ path }}
                </li>
              </ul>
              <h3>工作风格</h3>
              <p>{{ report.careerGuidance.workStyle }}</p>
              <h3>顺势建议</h3>
              <ul class="suggestion-list">
                <li v-for="(suggestion, index) in report.careerGuidance.developmentSuggestions" :key="index">
                  {{ suggestion }}
                </li>
              </ul>
            </div>
          </div>

            <!-- 关系模式 -->
          <div class="content-card">
            <h2>三、我如何与人相处 · 关系模式</h2>
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
            <h2>四、我卡在哪 · 破局行动</h2>
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
            <h2>五、知其序 · 行其路</h2>
            <p class="summary-text">{{ report.summary }}</p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="report-actions">
          <button class="btn-action primary" type="button" @click="goToCalendar">
            <IconMark class="icon" name="calendar" />
            打开决策日历
          </button>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { getReportDetail } from '../utils/aiService.js'

export default {
  name: 'ReportDetail',
  data() {
    return {
      report: null,
      foundationData: null,
      contentWithoutFoundation: '',
      loading: true,
      loadError: ''
    }
  },
  async mounted() {
    await this.loadReport()
  },
  methods: {
    async loadReport() {
      const reportId = this.$route.query.id
      try {
        const reportData = await getReportDetail(reportId)
        this.report = this.normalizeReportData(reportData)
        if (this.report.aiGeneratedContent) {
          this.parseFoundationData(this.report.aiGeneratedContent)
        }
      } catch (error) {
        this.loadError = error.response?.status === 403 ? '你没有权限查看这份报告' : '报告不存在或加载失败'
      } finally {
        this.loading = false
      }
    },
    normalizeReportData(report) {
      // 标准化数据结构，处理可能的字段名差异
      const rawBasicInfo = report.basicInfo || report.basic_info || {}
      const normalized = {
        basicInfo: {
          ...rawBasicInfo,
          name: rawBasicInfo.name || '用户',
          reportDate: rawBasicInfo.reportDate || rawBasicInfo.report_date || new Date().toISOString().split('T')[0]
        },
        structuredSections: report.structuredSections || report.structured_sections || null,
        energyProfile: report.energyProfile || report.energy_profile || {},
        careerGuidance: report.careerGuidance || report.career_guidance || {},
        relationshipPattern: report.relationshipPattern || report.relationship_pattern || {},
        personalGrowth: report.personalGrowth || report.personal_growth || {},
        summary: report.summary || '',
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
    formatMarkdown(content) {
      if (!content) return ''

      let html = content

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
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    }
  }
}
</script>

<style scoped>
.report-detail {
  width: 100%;
  background: var(--surface-strong, #fffaf0);
  min-height: 100dvh;
}

/* 报告头部 */
.report-header {
  padding: 100px 20px 40px;
  background: linear-gradient(135deg, rgba(255, 240, 223, .85) 0%, rgba(184, 92, 80, .22) 100%);
}

.btn-back {
  padding: 8px 16px;
  font-size: 14px;
  color: var(--muted, #7d6653);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  margin-bottom: 20px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease);
}

.btn-back:hover {
  background: #fff;
  color: var(--cinnabar-deep, #9e3f35);
}

.report-header h1 {
  font-size: 36px;
  font-weight: 700;
  color: var(--ink, #2f241b);
  margin-bottom: 15px;
}

.report-meta {
  font-size: 15px;
  color: var(--muted, #7d6653);
}

.divider {
  margin: 0 10px;
}

/* 容器 */
.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0;
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
  color: var(--ink, #2f241b);
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
}

.content-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink, #2f241b);
  margin: 20px 0 12px;
}

/* AI 内容 */
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar-deep, #9e3f35) 100%);
  color: #fff;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 25px;
}

.badge-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.markdown-content {
  line-height: 2;
  color: var(--muted, #7d6653);
}

.markdown-content h2 {
  font-size: 22px;
  margin-top: 50px;
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
  color: var(--ink, #2f241b);
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
  color: var(--cinnabar, #b85c50);
  font-weight: 600;
}

.markdown-content h4 {
  font-size: 16px;
  margin-top: 28px;
  margin-bottom: 15px;
  color: var(--muted, #7d6653);
  font-weight: 600;
}

.markdown-content h5 {
  font-size: 15px;
  margin-top: 22px;
  margin-bottom: 12px;
  color: var(--muted, #7d6653);
  font-weight: 600;
}

.markdown-content p {
  margin-bottom: 20px;
  text-align: justify;
}

.markdown-content hr {
  border: none;
  height: 3px;
  background: linear-gradient(to right, transparent, var(--cinnabar, #b85c50), transparent);
  margin: 45px 0;
  position: relative;
}

.markdown-content hr::before {
  content: '';
  width: 7px;
  height: 7px;
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%) rotate(45deg);
  background: #fff;
  border: 1px solid var(--cinnabar, #b85c50);
  color: var(--cinnabar, #b85c50);
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
  color: var(--cinnabar, #b85c50);
  font-weight: 600;
  font-size: 18px;
}

.markdown-content strong {
  color: var(--ink, #2f241b);
  font-weight: 600;
}

.section-icon {
  font-size: 24px;
}

/* 命理基础样式 */
.foundation-section {
  margin-bottom: 35px;
  padding-bottom: 25px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink, #2f241b);
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
}

.title-icon {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
}

.subsection-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--cinnabar, #b85c50);
  margin: 20px 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subsection-title::before {
  content: '◆';
  font-size: 14px;
  color: var(--cinnabar, #b85c50);
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
  background: linear-gradient(135deg, rgba(255, 240, 223, .64) 0%, rgba(255, 240, 223, .78) 100%);
  border: 1px solid rgba(184, 92, 80, .22);
  border-radius: 10px;
  padding: 18px;
  text-align: center;
  transition: border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease);
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
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar, #b85c50) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.pillar-card:hover {
  transform: none;
  box-shadow: 0 6px 16px rgba(212, 82, 79, 0.15);
  border-color: var(--cinnabar, #b85c50);
}

.pillar-card:hover::before {
  opacity: 1;
}

.pillar-card.day-pillar {
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar, #b85c50) 100%);
  border-color: var(--cinnabar, #b85c50);
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
  color: var(--muted, #7d6653);
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
  color: var(--cinnabar, #b85c50);
  margin-bottom: 6px;
  letter-spacing: 3px;
}

.pillar-god {
  font-size: 11px;
  color: var(--muted, #7d6653);
  background: rgba(255, 255, 255, 0.9);
  padding: 3px 9px;
  border-radius: 10px;
  display: inline-block;
  margin-top: 4px;
  border: 1px solid rgba(184, 92, 80, .22);
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
  background: linear-gradient(135deg, var(--surface, rgba(255, 250, 240, .78)) 0%, var(--surface-strong, #fffaf0) 100%);
  border: 1px solid rgba(139, 90, 20, .16);
  border-radius: 10px;
  padding: 16px;
  transition: border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease);
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
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar-deep, #9e3f35) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.palace-card:hover {
  transform: none;
  box-shadow: 0 6px 16px rgba(184, 92, 80, .15);
  border-color: var(--cinnabar, #b85c50);
}

.palace-card:hover::before {
  opacity: 1;
}

.palace-label {
  font-size: 13px;
  color: var(--muted, #7d6653);
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
  transition: box-shadow var(--motion-fast, 150ms) var(--ease-out, ease);
}

.star-tag.main {
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar-deep, #9e3f35) 100%);
  color: #fff;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.3);
}

.star-tag.main:hover {
  transform: none;
  box-shadow: 0 3px 8px rgba(102, 126, 234, 0.4);
}

.star-tag.aux {
  background: var(--line, rgba(139, 90, 20, .16));
  color: var(--muted, #7d6653);
  border: 1px solid rgba(139, 90, 20, .16);
}

.patterns-section {
  margin-top: 15px;
  padding: 14px;
  background: linear-gradient(135deg, rgba(255, 240, 223, .64) 0%, rgba(255, 240, 223, .78) 100%);
  border-radius: 8px;
  border-left: 3px solid var(--cinnabar, #b85c50);
}

.pattern-label {
  font-size: 13px;
  color: var(--muted, #7d6653);
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
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar, #b85c50) 100%);
  color: #fff;
  padding: 5px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(212, 82, 79, 0.3);
  transition: box-shadow var(--motion-fast, 150ms) var(--ease-out, ease);
}

.pattern-tag:hover {
  transform: none;
  box-shadow: 0 3px 8px rgba(212, 82, 79, 0.4);
}

/* 能量类型 */
.energy-type {
  margin-bottom: 20px;
}

.type-badge {
  display: inline-block;
  background: linear-gradient(135deg, var(--cinnabar, #b85c50) 0%, var(--cinnabar, #b85c50) 100%);
  color: #fff;
  padding: 10px 24px;
  border-radius: 25px;
  font-size: 18px;
  font-weight: 600;
}

.traits {
  font-size: 16px;
  color: var(--muted, #7d6653);
  margin-bottom: 15px;
}

.traits strong {
  color: var(--ink, #2f241b);
}

.description {
  font-size: 15px;
  line-height: 1.8;
  color: var(--muted, #7d6653);
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
  color: var(--muted, #7d6653);
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
  color: var(--cinnabar, #b85c50);
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
  background: var(--surface-strong, #fffaf0);
  padding: 20px;
  border-radius: 12px;
  border-left: 4px solid var(--cinnabar, #b85c50);
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
  background: var(--cinnabar, #b85c50);
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
  color: var(--muted, #7d6653);
  line-height: 1.8;
  margin-bottom: 8px;
}

/* 总结 */
.summary-card {
  background: linear-gradient(135deg, rgba(255, 240, 223, .78) 0%, rgba(184, 92, 80, .12) 100%);
  border: 2px solid var(--cinnabar, #b85c50);
}

.summary-text {
  font-size: 16px;
  line-height: 2;
  color: var(--muted, #7d6653);
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
  color: var(--ink, #2f241b);
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid var(--line, rgba(139, 90, 20, .16));
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
  background: linear-gradient(135deg, var(--surface-strong, #fffaf0) 0%, var(--paper-soft, #fffaf0) 100%);
  padding: 25px;
  border-radius: 12px;
  border-left: 4px solid var(--cinnabar, #b85c50);
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
  color: var(--cinnabar, #b85c50);
  margin: 0;
}

.subsection-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--muted, #7d6653);
  text-align: justify;
}

/* 议题章节 */
.topic-section {
  background: var(--paper-soft, #fffaf0);
  border: 1px solid rgba(139, 90, 20, .16);
}

.topic-subsections {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.topic-subsection {
  padding: 20px;
  background: var(--surface-strong, #fffaf0);
  border-radius: 8px;
}

.topic-subsection-title {
  font-size: 16px;
  color: var(--cinnabar, #b85c50);
  margin-bottom: 12px;
  font-weight: 600;
}

.topic-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--muted, #7d6653);
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
  background: var(--paper-soft, #fffaf0);
  border-radius: 8px;
  border: 1px solid rgba(139, 90, 20, .16);
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
  accent-color: var(--cinnabar, #b85c50);
}

.action-item-check label {
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
  color: var(--muted, #7d6653);
  cursor: pointer;
}

.action-item-check input[type="checkbox"]:checked + label {
  text-decoration: line-through;
  color: var(--muted, #7d6653);
}

/* 总结章节 */
.summary-section {
  background: linear-gradient(135deg, rgba(255, 240, 223, .78) 0%, rgba(184, 92, 80, .12) 100%);
  border: 2px solid var(--cinnabar, #b85c50);
}

.summary-highlight {
  background: var(--paper-soft, #fffaf0);
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid var(--cinnabar, #b85c50);
}

.summary-highlight h3 {
  font-size: 16px;
  color: var(--cinnabar, #b85c50);
  margin-bottom: 10px;
}

.summary-highlight p {
  font-size: 15px;
  line-height: 1.8;
  color: var(--muted, #7d6653);
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
  color: var(--ink, #2f241b);
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
  color: var(--muted, #7d6653);
  background: #fff;
  border: 2px solid rgba(139, 90, 20, .16);
  border-radius: 50px;
  transition: background var(--motion-standard, 220ms) var(--ease-out, ease), color var(--motion-standard, 220ms) var(--ease-out, ease), border-color var(--motion-standard, 220ms) var(--ease-out, ease), box-shadow var(--motion-standard, 220ms) var(--ease-out, ease), transform var(--motion-fast, 150ms) var(--ease-out, ease);
}

.btn-action:hover {
  border-color: var(--cinnabar, #b85c50);
  color: var(--cinnabar, #b85c50);
  transform: translateY(-2px);
}

.markdown-content {
  overflow-wrap: anywhere;
}

.markdown-content :deep(pre) {
  max-width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  overflow-wrap: normal;
}

.markdown-content :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
}

.btn-action.primary {
  background: var(--cinnabar, #b85c50);
  color: #fff;
  border-color: var(--cinnabar, #b85c50);
}

.btn-action.primary:hover {
  background: var(--cinnabar-deep, #9e3f35);
  border-color: var(--cinnabar-deep, #9e3f35);
}

.icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
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
  .report-header {
    padding: 54px 20px 30px;
  }

  .report-header h1 {
    max-width: 100%;
    font-size: clamp(26px, 8vw, 34px);
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .report-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
    line-height: 1.6;
  }

  .divider {
    margin: 0;
  }

  .content-card {
    margin-bottom: 18px;
    padding: 24px 18px;
  }

  .report-content {
    padding: 28px 0 calc(60px + var(--safe-bottom, 0px));
  }

  .content-card h2,
  .section-title {
    gap: 8px;
    font-size: 20px;
    line-height: 1.35;
  }

  .markdown-content {
    font-size: 16px;
    line-height: 1.85;
  }

  .markdown-content h2 {
    margin-top: 36px;
    margin-bottom: 18px;
    padding-bottom: 11px;
    font-size: 20px;
  }

  .markdown-content h3 {
    margin-top: 26px;
    margin-bottom: 12px;
    font-size: 17px;
  }

  .markdown-content p {
    margin-bottom: 16px;
    text-align: left;
  }

  .markdown-content li {
    padding-left: 20px;
    line-height: 1.75;
  }

  .ai-badge {
    max-width: 100%;
    margin-bottom: 18px;
    padding: 8px 12px;
    font-size: 13px;
  }

  .pillar-card {
    padding: 14px 10px;
  }

  .pillar-value {
    font-size: 22px;
    letter-spacing: 2px;
  }

  .palace-card {
    padding: 14px;
  }

  .type-badge {
    max-width: 100%;
    padding: 9px 18px;
    font-size: 16px;
  }

  .two-columns {
    grid-template-columns: 1fr;
  }

  .report-actions {
    flex-direction: column;
    gap: 10px;
    margin-top: 28px;
  }

  .btn-action {
    width: 100%;
    min-height: 48px;
    justify-content: center;
  }

  .pillar-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .palace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 380px) {
  .report-header,
  .container {
    padding-right: 15px;
    padding-left: 15px;
  }

  .content-card {
    padding-right: 15px;
    padding-left: 15px;
  }

  .pillar-grid {
    gap: 8px;
  }

  .pillar-label {
    font-size: 11px;
  }
}

/* 报告页采用同一套纸张阅读层，长文本在手机上更像连续阅读而不是后台白板。 */
.report-detail {
  background: transparent;
}

.report-header {
  position: relative;
  overflow: hidden;
  padding: 62px 0 48px;
  background:
    linear-gradient(104deg, rgba(255, 250, 240, 0.9), rgba(255, 239, 222, 0.72)),
    radial-gradient(circle at 88% 18%, rgba(111, 159, 147, 0.2), transparent 25%),
    var(--paper-deep, #ead9bf);
}

.report-header::after {
  content: "说明书";
  position: absolute;
  right: 4%;
  bottom: -33px;
  color: rgba(184, 92, 80, 0.08);
  font-family: var(--font-display, serif);
  font-size: 110px;
  font-weight: 900;
  line-height: 1;
  pointer-events: none;
}

.report-header .container {
  position: relative;
  z-index: 1;
}

.report-header h1 {
  font-family: var(--font-display, serif);
  color: var(--ink, #2f241b);
  letter-spacing: 0.01em;
}

.report-meta {
  color: var(--muted, #7d6653);
}

.btn-back {
  border: 1px solid rgba(139, 90, 20, 0.16);
  background: rgba(255, 252, 245, 0.72);
  color: var(--cinnabar-deep, #9e3f35);
}

.report-content {
  background: transparent;
}

.content-card {
  border: 1px solid rgba(139, 90, 20, 0.13);
  background:
    linear-gradient(180deg, rgba(255, 252, 245, 0.92), rgba(255, 247, 231, 0.72));
  box-shadow: var(--shadow-card, 0 16px 48px -34px rgba(84, 48, 25, 0.48));
}

.content-card h2,
.section-title {
  font-family: var(--font-display, serif);
  color: var(--ink, #2f241b);
}

.ai-badge,
.type-badge,
.pattern-tag {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  box-shadow: 0 10px 22px -16px rgba(158, 63, 53, 0.86);
}

.markdown-content,
.description,
.traits,
.path-list li,
.suggestion-list li,
.trait-list li,
.action-detail,
.action-timeline,
.summary-text {
  color: var(--ink-soft, rgba(47, 36, 27, 0.68));
}

.markdown-content h2,
.content-card h2,
.section-title {
  border-bottom-color: rgba(139, 90, 20, 0.13);
}

.star-tag.main {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
}

.report-actions {
  gap: 10px;
}

.btn-action {
  border-color: rgba(139, 90, 20, 0.18);
  background: rgba(255, 252, 245, 0.82);
  color: var(--cinnabar-deep, #9e3f35);
}

.btn-action.primary {
  border-color: var(--cinnabar-deep, #9e3f35);
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
}

.summary-card,
.summary-section {
  border-color: rgba(184, 92, 80, 0.3);
  background: linear-gradient(145deg, rgba(255, 247, 231, 0.94), rgba(255, 232, 220, 0.78));
}

/* 移动端最终密度：报告按阅读流排列，减少卡片边距与标题占高。 */
@media (max-width: 768px) {
  .report-header {
    padding: 38px 0 24px;
  }

  .report-header::after {
    right: 2%;
    bottom: -20px;
    font-size: 72px;
  }

  .report-header h1 {
    font-size: clamp(24px, 7vw, 32px);
  }

  .report-content {
    padding-top: 20px;
    padding-bottom: calc(48px + var(--safe-bottom, 0px));
  }

  .content-card {
    margin-bottom: 12px;
    padding: 16px 14px;
    border-radius: 14px;
  }

  .content-card h2,
  .section-title {
    gap: 7px;
    font-size: 19px;
  }

  .subsection-title {
    font-size: 16px;
  }

  .pillar-grid {
    gap: 7px;
  }

  .pillar-card {
    padding: 11px 8px;
    border-radius: 11px;
  }

  .pillar-value {
    font-size: 20px;
  }

  .palace-card {
    padding: 12px;
    border-radius: 11px;
  }

  .markdown-content {
    line-height: 1.8;
  }

  .markdown-content h2 {
    margin-top: 28px;
    margin-bottom: 14px;
    padding-bottom: 9px;
    font-size: 19px;
  }

  .markdown-content h3 {
    margin-top: 22px;
    margin-bottom: 10px;
    font-size: 16px;
  }

  .type-badge {
    padding: 8px 14px;
    font-size: 15px;
  }

  .summary-highlight,
  .summary-message {
    padding: 14px;
  }

  .report-actions {
    gap: 8px;
    margin-top: 20px;
  }

  .btn-action {
    min-height: 46px;
    padding: 0 16px;
    font-size: 14px;
  }

  .btn-back,
  .btn-action {
    min-height: 46px;
  }

  .btn-action {
    width: 100%;
  }
}

/* 按钮专项：返回动作弱化，唯一主行动按钮固定在报告阅读流末端。 */
.btn-back,
.btn-action {
  display: inline-flex;
  min-height: var(--button-height, 46px);
  align-items: center;
  justify-content: center;
  border-radius: var(--button-radius, 13px);
  padding: 0 16px;
  font-family: var(--font-ui, sans-serif);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
}

.btn-back {
  margin-bottom: 16px;
  border: 1px solid rgba(139, 90, 20, 0.16);
  background: rgba(255, 252, 245, 0.72);
  color: var(--cinnabar-deep, #9e3f35);
}

.btn-action {
  border: 1px solid var(--cinnabar-deep, #9e3f35);
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), var(--cinnabar-deep, #9e3f35));
  color: #fffaf0;
  box-shadow: 0 10px 22px -16px rgba(158, 63, 53, 0.86);
}

.btn-back:hover,
.btn-back:focus-visible {
  background: rgba(184, 92, 80, 0.08);
}

.btn-action:hover {
  background: linear-gradient(145deg, var(--cinnabar, #b5574c), #8f352f);
  transform: none;
}

</style>
