<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Button as VanButton } from 'vant'
import ReportContentBlock from './ReportContentBlock.vue'
import { formatReportMarkdown } from '../report-markdown.js'

const props = defineProps({
  document: { type: Object, required: true }
})

const readerRef = ref(null)
const pageStageRef = ref(null)
const tocButtonRef = ref(null)
const currentPage = ref(0)
const pageInput = ref('01')
const tocOpen = ref(false)
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
const hasSummary = computed(() => Boolean(
  documentModel.value.summary?.content || documentModel.value.summary?.blocks.length
))
const hasDocumentContent = computed(() => documentModel.value.sections.length > 0 || chapterItems.value.length > 0)
const firstContentPageIndex = computed(() => 2 + (chapterItems.value.length ? 1 : 0))
const pageCount = computed(() => 2
  + (chapterItems.value.length ? 1 : 0)
  + documentModel.value.sections.length
  + (hasSummary.value ? 1 : 0)
  + (hasDocumentContent.value ? 0 : 1))
const readerTocItems = computed(() => chapterItems.value.map((chapter, index) => ({
  ...chapter,
  pageIndex: firstContentPageIndex.value + index,
  pageNumber: firstContentPageIndex.value + index + 1
})))
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

watch(currentPage, value => {
  pageInput.value = String(value + 1).padStart(2, '0')
})

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

function scrollToCurrentPage() {
  nextTick(() => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    pageStageRef.value?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' })
  })
}

function goToPage(index, focusStage = false) {
  const nextPage = Math.min(Math.max(Number(index) || 0, 0), pageCount.value - 1)
  currentPage.value = nextPage
  pageInput.value = String(nextPage + 1).padStart(2, '0')
  tocOpen.value = false
  if (focusStage) {
    nextTick(() => pageStageRef.value?.focus({ preventScroll: true }))
  }
  scrollToCurrentPage()
}

function jumpToPage() {
  if (!/^\d+$/.test(pageInput.value.trim())) {
    pageInput.value = String(currentPage.value + 1).padStart(2, '0')
    return
  }
  const requestedPage = Number(pageInput.value)
  goToPage(Math.min(Math.max(requestedPage, 1), pageCount.value) - 1)
}

function toggleContents() {
  tocOpen.value = !tocOpen.value
  if (tocOpen.value) {
    nextTick(() => readerRef.value?.querySelector('.report-reader__toc-item')?.focus())
  } else {
    nextTick(focusContentsButton)
  }
}

function closeContents() {
  if (!tocOpen.value) return
  tocOpen.value = false
  nextTick(focusContentsButton)
}

function focusContentsButton() {
  const button = tocButtonRef.value?.$el || tocButtonRef.value
  button?.focus?.()
}

function handleReaderKeydown(event) {
  if (event.key === 'Escape' && tocOpen.value) {
    event.preventDefault()
    closeContents()
    return
  }
  if (event.key === 'Tab' && tocOpen.value) {
    const items = [...(readerRef.value?.querySelectorAll('.report-reader__toc-item') || [])]
    const activeIndex = items.indexOf(document.activeElement)
    if (!items.length) return
    if (activeIndex < 0 || (event.shiftKey && activeIndex === 0)) {
      event.preventDefault()
      items[items.length - 1].focus()
    } else if (!event.shiftKey && activeIndex === items.length - 1) {
      event.preventDefault()
      items[0].focus()
    }
    return
  }
  if (tocOpen.value || event.target.closest?.('button, input, textarea, select, a, [contenteditable="true"]')) return
  if (['ArrowRight', 'PageDown'].includes(event.key) && currentPage.value < pageCount.value - 1) {
    event.preventDefault()
    goToPage(currentPage.value + 1)
  } else if (['ArrowLeft', 'PageUp'].includes(event.key) && currentPage.value > 0) {
    event.preventDefault()
    goToPage(currentPage.value - 1)
  }
}

function advanceFromPage(event) {
  if (event.target.closest?.('button, input, textarea, select, a, [contenteditable="true"]')) return
  if (window.getSelection?.()?.toString()) return
  if (currentPage.value < pageCount.value - 1) goToPage(currentPage.value + 1)
}
</script>

<template>
  <div ref="readerRef" class="report-reader" @keydown="handleReaderKeydown">
    <div v-if="chapterItems.length" class="report-reader__topbar">
      <VanButton
        ref="tocButtonRef"
        type="default"
        plain
        native-type="button"
        class="report-reader__toc-toggle"
        aria-controls="report-reader-toc"
        :aria-expanded="tocOpen"
        @click.stop="toggleContents"
      >
        查看目录
        <span class="report-reader__chevron" :class="{ 'is-open': tocOpen }" aria-hidden="true"></span>
      </VanButton>
    </div>

    <div v-if="tocOpen" class="report-reader__toc-scrim" @click="closeContents">
      <div id="report-reader-toc" class="report-reader__toc-panel" role="dialog" aria-modal="true" aria-label="人生说明书目录" @click.stop>
        <p class="report-reader__toc-heading">阅读目录</p>
        <nav aria-label="人生说明书目录条目">
          <ol>
            <li v-for="item in readerTocItems" :key="item.id">
              <button
                type="button"
                class="report-reader__toc-item"
                :aria-current="currentPage === item.pageIndex ? 'page' : undefined"
                @click="goToPage(item.pageIndex, true)"
              >
                <span class="report-reader__toc-title">{{ item.title }}</span>
                <span class="report-reader__toc-leader" aria-hidden="true"></span>
                <span class="report-reader__toc-page">{{ String(item.pageNumber).padStart(2, '0') }}</span>
              </button>
            </li>
          </ol>
        </nav>
      </div>
    </div>

    <div
      ref="pageStageRef"
      class="report-reader__stage"
      role="region"
      tabindex="0"
      :aria-label="`报告阅读页 ${currentPage + 1} / ${pageCount}。使用方向键或 Page Up、Page Down 翻页。`"
      @click="advanceFromPage"
    >
      <article class="report-document" data-render-ready="true">
    <section class="report-page report-page--cover" :class="{ 'report-page--reader-hidden': currentPage !== 0 }" aria-label="报告封面">
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

    <section class="report-page report-page--intro" :class="{ 'report-page--reader-hidden': currentPage !== 1 }" aria-labelledby="report-intro-title">
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

    <section v-if="chapterItems.length" class="report-page report-page--toc" :class="{ 'report-page--reader-hidden': currentPage !== 2 }" aria-labelledby="report-toc-title">
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
      :class="{
        'report-page--foundation': section.kind === 'foundation',
        'report-page--markdown': section.kind === 'markdown',
        'report-page--reader-hidden': currentPage !== firstContentPageIndex + index
      }"
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

    <section v-if="hasSummary" class="report-page report-page--ending report-page--dark" :class="{ 'report-page--reader-hidden': currentPage !== firstContentPageIndex + documentModel.sections.length }" aria-labelledby="report-summary-title">
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

    <section v-if="!hasDocumentContent" class="report-page report-page--empty" :class="{ 'report-page--reader-hidden': currentPage !== 2 }" aria-live="polite">
      <div class="report-page__body">
        <div class="report-heading"><h2>报告正文暂不可用</h2></div>
      </div>
    </section>
      </article>
    </div>

    <div class="report-reader__pagination" role="group" aria-label="报告页码导航">
      <VanButton
        type="default"
        plain
        native-type="button"
        class="report-reader__page-button"
        :disabled="currentPage === 0"
        @click="goToPage(currentPage - 1)"
      >上一页</VanButton>
      <label class="report-reader__page-label">
        <span>第</span>
        <input
          v-model="pageInput"
          type="text"
          inputmode="numeric"
          pattern="[0-9]*"
          autocomplete="off"
          aria-label="跳转到第几页"
          @change="jumpToPage"
          @keydown.enter.prevent="jumpToPage"
        >
        <span>/ {{ pageCount }} 页</span>
      </label>
      <VanButton
        type="default"
        plain
        native-type="button"
        class="report-reader__page-button"
        :disabled="currentPage >= pageCount - 1"
        @click="goToPage(currentPage + 1)"
      >下一页</VanButton>
    </div>
    <p class="report-reader__hint" aria-hidden="true">也可以点击报告页面进入下一页</p>
    <span class="report-reader__live-status" role="status" aria-live="polite">第 {{ currentPage + 1 }} 页，共 {{ pageCount }} 页</span>
  </div>
</template>

<style src="../styles/report-document.css"></style>
<style src="../styles/report-reader.css"></style>
