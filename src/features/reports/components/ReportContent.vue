<script setup>
import { formatReportMarkdown } from '../report-content.js'

defineProps({
  report: { type: Object, required: true },
  foundationData: { type: Object, default: null },
  contentWithoutFoundation: { type: String, default: '' }
})
</script>

<template>
  <div v-if="report.structuredSections?.length" class="authored-content">
    <article v-for="section in report.structuredSections" :key="section.fragment_key" class="content-card authored-section">
      <p class="section-eyebrow">{{ section.section_title }}</p>
      <h2>{{ section.title || section.section_title }}</h2>
      <p class="authored-section-content">{{ section.content }}</p>
    </article>
  </div>

  <div v-else-if="report.aiGeneratedContent" class="ai-content">
    <div class="content-card">
      <div class="ai-badge">
        <IconMark class="badge-icon" name="spark" />
        <span>辰鉴结构化解读</span>
      </div>

      <div v-if="foundationData" class="foundation-section">
        <h2 class="section-title">
          <IconMark class="title-icon" name="compass" />
          先天坐标
        </h2>

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

      <div class="markdown-content" v-html="formatReportMarkdown(contentWithoutFoundation)"></div>
    </div>
  </div>

  <div v-else class="structured-content">
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

    <div class="content-card">
      <h2>二、我往哪去 · 环境与方向</h2>
      <div class="section-content">
        <h3>可以尝试的方向</h3>
        <ul class="path-list">
          <li v-for="(path, index) in report.careerGuidance.suitablePaths" :key="index">{{ path }}</li>
        </ul>
        <h3>工作风格</h3>
        <p>{{ report.careerGuidance.workStyle }}</p>
        <h3>顺势建议</h3>
        <ul class="suggestion-list">
          <li v-for="(suggestion, index) in report.careerGuidance.developmentSuggestions" :key="index">{{ suggestion }}</li>
        </ul>
      </div>
    </div>

    <div class="content-card">
      <h2>三、我如何与人相处 · 关系模式</h2>
      <div class="section-content">
        <h3>关系风格</h3>
        <p>{{ report.relationshipPattern.style }}</p>
        <div class="two-columns">
          <div class="column">
            <h3>优势</h3>
            <ul class="trait-list">
              <li v-for="(strength, index) in report.relationshipPattern.strengths" :key="index">{{ strength }}</li>
            </ul>
          </div>
          <div class="column">
            <h3>挑战</h3>
            <ul class="trait-list">
              <li v-for="(challenge, index) in report.relationshipPattern.challenges" :key="index">{{ challenge }}</li>
            </ul>
          </div>
        </div>
        <h3>成长方向</h3>
        <p>{{ report.relationshipPattern.growthDirection }}</p>
      </div>
    </div>

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

    <div class="content-card summary-card">
      <h2>五、知其序 · 行其路</h2>
      <p class="summary-text">{{ report.summary }}</p>
    </div>
  </div>
</template>

<style scoped src="../styles/report-content-base.css"></style>
<style scoped src="../styles/report-foundation.css"></style>
<style scoped src="../styles/report-content.css"></style>
<style scoped src="../styles/report-content-layout.css"></style>
<style scoped src="../styles/report-content-overrides.css"></style>
<style scoped>
.authored-content { display: grid; gap: 16px; }
.authored-section { margin: 0; }
.section-eyebrow { margin: 0 0 8px; color: var(--gold-deep, #8a621b); font-size: 12px; font-weight: var(--weight-semibold); }
.authored-section h2 { margin: 0 0 12px; }
.authored-section-content { margin: 0; line-height: 1.9; white-space: pre-line; overflow-wrap: anywhere; }
</style>
