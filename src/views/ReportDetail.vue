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
import { formatReportMarkdown, normalizeReportData, parseLegacyReportContent } from '../features/reports/report-content.js'

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
        this.report = normalizeReportData(reportData)
        if (this.report.contentPayload?.foundation_data) {
          this.foundationData = this.report.contentPayload.foundation_data
        } else if (this.report.aiGeneratedContent) {
          const parsed = parseLegacyReportContent(this.report.aiGeneratedContent)
          this.foundationData = parsed.foundationData
          this.contentWithoutFoundation = parsed.contentWithoutFoundation
        }
      } catch (error) {
        this.loadError = error.response?.status === 403 ? '你没有权限查看这份报告' : '报告不存在或加载失败'
      } finally {
        this.loading = false
      }
    },
    formatMarkdown(content) {
      return formatReportMarkdown(content)
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

<style scoped src="../features/reports/styles/report-detail-base.css"></style>
<style scoped src="../features/reports/styles/report-foundation.css"></style>
<style scoped src="../features/reports/styles/report-content.css"></style>
<style scoped src="../features/reports/styles/report-layout.css"></style>
<style scoped src="../features/reports/styles/report-responsive-overrides.css"></style>
