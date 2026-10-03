<script setup>
import { computed } from 'vue'
import ReportContentBlock from './ReportContentBlock.vue'
import { formatReportMarkdown } from '../report-markdown.js'

const props = defineProps({
  document: { type: Object, required: true }
})

const displayName = computed(() => props.document.recipient || '')
const displayTitle = computed(() => props.document.title || '人生说明书')
const reportDate = computed(() => props.document.reportDate || '')
const reportIdentity = computed(() => displayName.value ? `人生说明书 · ${displayName.value}` : '人生说明书')
const documentModel = computed(() => props.document)
const chapterItems = computed(() => {
  const chapters = documentModel.value.sections.map(section => ({
    id: section.id,
    title: section.title
  }))
  if (documentModel.value.summary?.content || documentModel.value.summary?.blocks.length) {
    chapters.push({ id: 'summary', title: '总结与寄语' })
  }
  return chapters
})
const foundationSection = computed(() => documentModel.value.sections.find(section => section.kind === 'foundation'))
const foundationData = computed(() => foundationSection.value?.foundationData || {})
const baziPillars = computed(() => {
  const bazi = foundationData.value?.bazi
  if (!bazi) return []
  return [
    ['年柱', bazi.year],
    ['月柱', bazi.month],
    ['日柱', bazi.day],
    ['时柱', bazi.hour]
  ].filter(([, pillar]) => pillar)
})
const ziweiPalaces = computed(() => {
  const ziwei = foundationData.value?.ziwei
  if (!ziwei) return []
  return [
    ['命宫', ziwei.life_palace],
    ['事业宫', ziwei.career_palace],
    ['财帛宫', ziwei.wealth_palace],
    ['夫妻宫', ziwei.relationship_palace]
  ].filter(([, palace]) => palace)
})
const additionalFoundation = computed(() => foundationSection.value?.foundationExtras || null)
const hasDocumentContent = computed(() => documentModel.value.sections.length > 0 || chapterItems.value.length > 0)

function chapterNumber(index) {
  return String(index + 1).padStart(2, '0')
}

function pillarText(pillar) {
  if (typeof pillar === 'string') return pillar
  return `${pillar?.stem || ''}${pillar?.branch || ''}`
}

function joinStars(palace) {
  return [...(palace?.main_stars || []), ...(palace?.aux_stars || [])].filter(Boolean).join(' · ')
}
</script>

<template>
  <article class="report-document" data-render-ready="true">
    <section class="report-page report-page--cover" aria-label="报告封面">
      <div class="report-cover__frame">
        <div class="report-cover__mark" aria-hidden="true"><span></span></div>
        <p class="report-cover__eyebrow">辰鉴 · PERSONAL MAP</p>
        <h1 class="report-cover__title">{{ displayTitle }}</h1>
        <div class="report-cover__rule" aria-hidden="true"></div>
        <p v-if="displayName" class="report-cover__name">{{ displayName }}</p>
        <p class="report-cover__intro">这不是一份命理决断，也不是一份心理诊断<br>这是一张属于你的地图</p>
        <p class="report-cover__footer">星辰引路 · 镜子照见<br>（辰鉴出品）</p>
      </div>
    </section>

    <section class="report-page report-page--intro" aria-labelledby="report-intro-title">
      <div class="report-page__running"><span>序言</span><span>{{ reportIdentity }}</span></div>
      <div class="report-page__body report-intro">
        <p class="report-page__eyebrow">{{ reportIdentity }}</p>
        <h2 id="report-intro-title">从这里开始，读一读自己</h2>
        <div class="report-rule" aria-hidden="true"></div>
        <div class="report-prose">
          <p>这份报告把不同的观察放在同一张地图上，帮助你看见自己的特质、正在经历的议题，以及可能的下一步。</p>
          <p>它是一份供你参考的阅读材料，不替你下定义。对你有帮助的部分，可以带回生活慢慢验证。</p>
        </div>
      </div>
      <div v-if="reportDate" class="report-page__footer"><span>报告日期 · {{ reportDate }}</span></div>
    </section>

    <section v-if="chapterItems.length" class="report-page report-page--toc" aria-labelledby="report-toc-title">
      <div class="report-page__running"><span>目录</span><span>{{ reportIdentity }}</span></div>
      <div class="report-page__body">
        <div class="report-heading report-heading--large">
          <span class="report-heading__prefix">目 录</span>
          <h2 id="report-toc-title">阅读路径</h2>
        </div>
        <ol class="report-toc">
          <li v-for="(chapter, index) in chapterItems" :key="chapter.id">
            <span class="report-toc__index">{{ chapterNumber(index) }}</span>
            <span class="report-toc__copy"><strong>{{ chapter.title }}</strong></span>
            <span class="report-toc__leader" aria-hidden="true"></span>
          </li>
        </ol>
      </div>
      <div class="report-page__footer"><span>辰鉴 · 个人报告</span></div>
    </section>

    <section
      v-for="(section, index) in documentModel.sections"
      :key="section.id"
      class="report-page report-page--content"
      :class="{ 'report-page--foundation': section.kind === 'foundation', 'report-page--markdown': section.kind === 'markdown' }"
      :aria-labelledby="`report-section-title-${index}`"
    >
      <div class="report-page__running"><span>{{ chapterNumber(index) }} · {{ section.title }}</span><span>{{ reportIdentity }}</span></div>
      <div class="report-page__body">
        <div class="report-heading">
          <span class="report-heading__prefix">{{ chapterNumber(index) }}</span>
          <h2 :id="`report-section-title-${index}`">{{ section.title }}</h2>
        </div>

        <p v-if="section.subtitle" class="report-lead">{{ section.subtitle }}</p>
        <div v-if="section.kind === 'markdown' && section.content" class="report-markdown-content" v-html="formatReportMarkdown(section.content)"></div>
        <div v-else-if="section.content" class="report-section-intro report-markdown-content" v-html="formatReportMarkdown(section.content)"></div>

        <div v-if="section.kind === 'foundation'" class="report-foundation-content">
          <div v-if="baziPillars.length" class="report-grid report-grid--four">
            <div v-for="([label, pillar]) in baziPillars" :key="label" class="report-card report-card--center">
              <span class="report-card__label">{{ label }}</span>
              <strong class="report-card__value">{{ pillarText(pillar) }}</strong>
              <small v-if="pillar.ten_god">{{ pillar.ten_god }}</small>
            </div>
          </div>
          <div v-if="foundationData.bazi?.day_master" class="report-callout">
            <span class="report-callout__label">日主</span>
            <p>{{ foundationData.bazi.day_master }}</p>
          </div>
          <div v-if="foundationData.ziwei?.patterns?.length" class="report-callout">
            <span class="report-callout__label">格局</span>
            <p>{{ foundationData.ziwei.patterns.join(' · ') }}</p>
          </div>
          <div v-if="ziweiPalaces.length" class="report-card-stack">
            <div v-for="([label, palace]) in ziweiPalaces" :key="label" class="report-card">
              <span class="report-card__label">{{ label }}</span>
              <p>{{ joinStars(palace) }}</p>
            </div>
          </div>
          <ReportContentBlock v-if="additionalFoundation" :block="additionalFoundation" />
        </div>

        <ul v-if="section.items?.length" class="report-list report-list--spaced">
          <li v-for="(item, itemIndex) in section.items" :key="`${section.id}-item-${itemIndex}`">{{ item }}</li>
        </ul>
        <ReportContentBlock
          v-for="block in section.blocks"
          :key="block.id"
          :block="block"
        />
      </div>
      <div class="report-page__footer"><span>{{ chapterNumber(index) }} · {{ section.title }}</span></div>
    </section>

    <section v-if="documentModel.summary?.content || documentModel.summary?.blocks.length" class="report-page report-page--ending report-page--dark" aria-labelledby="report-summary-title">
      <div class="report-ending">
        <p class="report-divider__number">{{ chapterNumber(documentModel.sections.length) }}</p>
        <h2 id="report-summary-title">总结与寄语</h2>
        <div class="report-rule" aria-hidden="true"></div>
        <blockquote v-if="documentModel.summary.content" class="report-markdown-content" v-html="formatReportMarkdown(documentModel.summary.content)"></blockquote>
        <ReportContentBlock
          v-for="block in documentModel.summary.blocks"
          :key="block.id"
          :block="block"
          class="report-ending__block"
        />
        <p class="report-ending__signature">辰鉴 · 星辰引路，镜子照见</p>
      </div>
    </section>

    <section v-if="!hasDocumentContent" class="report-page report-page--empty" aria-live="polite">
      <div class="report-page__body">
        <div class="report-heading"><h2>报告正文暂不可用</h2></div>
      </div>
    </section>
  </article>
</template>

<style src="../styles/report-document.css"></style>
