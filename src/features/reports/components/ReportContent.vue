<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
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
const readerMode = ref('paged')
const isContinuous = computed(() => readerMode.value === 'continuous')
let pageObserver = null
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
const sectionPageEntries = computed(() => {
  let pageIndex = firstContentPageIndex.value
  return documentModel.value.sections.flatMap((section, sectionIndex) => {
    const contents = section.readerPages?.length ? section.readerPages : [section.content || '']
    return contents.map((content, pageInSection) => ({
      section,
      sectionIndex,
      content,
      pageInSection,
      pageIndex: pageIndex++
    }))
  })
})
const summaryPageIndex = computed(() => firstContentPageIndex.value + sectionPageEntries.value.length)
const pageCount = computed(() => firstContentPageIndex.value
  + sectionPageEntries.value.length
  + (hasSummary.value ? 1 : 0)
  + (hasDocumentContent.value ? 0 : 1))
const readerTocItems = computed(() => {
  let pageIndex = firstContentPageIndex.value
  return chapterItems.value.map((chapter, index) => {
    const chapterPageCount = index < documentModel.value.sections.length
      ? (documentModel.value.sections[index].readerPages?.length || 1)
      : 1
    const item = {
      ...chapter,
      pageIndex,
      pageNumber: pageIndex + 1,
      endPageIndex: pageIndex + chapterPageCount
    }
    pageIndex += chapterPageCount
    return item
  })
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

function scrollToPage(pageIndex, mode = readerMode.value, requestedBehavior = 'smooth', afterScroll, waitForLayout = false) {
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const behavior = requestedBehavior === 'smooth' && !reducedMotion ? 'smooth' : 'instant'
  const scroll = () => {
    const target = mode === 'continuous'
      ? readerRef.value?.querySelector(`[data-reader-page="${pageIndex + 1}"]`)
      : pageStageRef.value
    target?.scrollIntoView({ behavior, block: 'start' })
    afterScroll?.()
  }
  if (waitForLayout) nextTick(() => requestAnimationFrame(scroll))
  else scroll()
}

function goToPage(index, focusStage = false) {
  const nextPage = Math.min(Math.max(Number(index) || 0, 0), pageCount.value - 1)
  currentPage.value = nextPage
  pageInput.value = String(nextPage + 1).padStart(2, '0')
  tocOpen.value = false
  if (focusStage) {
    nextTick(() => pageStageRef.value?.focus({ preventScroll: true }))
  }
  scrollToPage(nextPage, readerMode.value, isContinuous.value ? 'auto' : 'smooth')
}

function jumpToPage() {
  if (!/^\d+$/.test(pageInput.value.trim())) {
    pageInput.value = String(currentPage.value + 1).padStart(2, '0')
    return
  }
  const requestedPage = Number(pageInput.value)
  goToPage(Math.min(Math.max(requestedPage, 1), pageCount.value) - 1)
}

function observeContinuousPages() {
  pageObserver?.disconnect()
  if (!isContinuous.value || typeof IntersectionObserver === 'undefined') return

  const viewportHeight = window.innerHeight || document.documentElement.clientHeight
  const readingBandTop = Math.round(viewportHeight * 0.18)
  const readingBandBottom = Math.round(viewportHeight * 0.72)
  pageObserver = new IntersectionObserver(() => {
    currentPage.value = pageAtReadingPosition()
  }, {
    rootMargin: `-${readingBandTop}px 0px -${readingBandBottom}px 0px`,
    threshold: 0
  })

  readerRef.value?.querySelectorAll('[data-reader-page]').forEach(page => pageObserver.observe(page))
}

function pageAtReadingPosition() {
  const readingLine = window.innerHeight * 0.24
  const visiblePages = [...(readerRef.value?.querySelectorAll('[data-reader-page]') || [])]
    .filter(page => page.getClientRects().length)
  const pageAtLine = visiblePages.find(page => {
    const bounds = page.getBoundingClientRect()
    return bounds.top <= readingLine && bounds.bottom >= readingLine
  })
  const nearestPage = pageAtLine || visiblePages.reduce((nearest, page) => {
    const bounds = page.getBoundingClientRect()
    const nearestBounds = nearest.getBoundingClientRect()
    const distance = Math.max(bounds.top - readingLine, readingLine - bounds.bottom, 0)
    const nearestDistance = Math.max(nearestBounds.top - readingLine, readingLine - nearestBounds.bottom, 0)
    return distance < nearestDistance ? page : nearest
  }, visiblePages[0])
  const pageIndex = Number(nearestPage?.dataset.readerPage) - 1
  return Number.isInteger(pageIndex) ? Math.min(Math.max(pageIndex, 0), pageCount.value - 1) : currentPage.value
}

function setReaderMode(mode) {
  if (!['paged', 'continuous'].includes(mode) || mode === readerMode.value) return

  const pageToKeep = isContinuous.value ? pageAtReadingPosition() : currentPage.value
  pageObserver?.disconnect()
  currentPage.value = pageToKeep
  readerMode.value = mode
  scrollToPage(pageToKeep, mode, 'auto', () => {
    if (mode === 'continuous') observeContinuousPages()
  }, true)
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
  if (tocOpen.value || event.target.closest?.('input, textarea, select, a, [contenteditable="true"]')) return
  const nextKeys = isContinuous.value ? ['ArrowRight'] : ['ArrowRight', 'PageDown']
  const previousKeys = isContinuous.value ? ['ArrowLeft'] : ['ArrowLeft', 'PageUp']
  if (nextKeys.includes(event.key) && currentPage.value < pageCount.value - 1) {
    event.preventDefault()
    goToPage(currentPage.value + 1)
  } else if (previousKeys.includes(event.key) && currentPage.value > 0) {
    event.preventDefault()
    goToPage(currentPage.value - 1)
  }
}

function advanceFromPage(event) {
  if (event.target.closest?.('button, input, textarea, select, a, [contenteditable="true"]')) return
  if (window.getSelection?.()?.toString()) return
  pageStageRef.value?.focus({ preventScroll: true })
  if (!isContinuous.value && currentPage.value < pageCount.value - 1) goToPage(currentPage.value + 1)
}

onBeforeUnmount(() => pageObserver?.disconnect())
</script>

<template>
  <div ref="readerRef" class="report-reader" :class="{ 'report-reader--continuous': isContinuous }" @keydown="handleReaderKeydown">
    <div class="report-reader__topbar">
      <div class="report-reader__topbar-actions">
        <label class="report-reader__mode-control">
          <span class="report-reader__mode-label">阅读方式</span>
          <span class="report-reader__mode-select-wrap">
            <select
              class="report-reader__mode-select"
              aria-label="阅读方式"
              :value="readerMode"
              @change="setReaderMode($event.target.value)"
            >
              <option value="paged">分页阅读</option>
              <option value="continuous">连续阅读</option>
            </select>
            <span class="report-reader__mode-chevron" aria-hidden="true"></span>
          </span>
        </label>
        <VanButton
          v-if="chapterItems.length"
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
                :aria-current="currentPage >= item.pageIndex && currentPage < item.endPageIndex ? 'page' : undefined"
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
      :aria-label="`报告阅读页 ${currentPage + 1} / ${pageCount}。使用左右方向键翻页。`"
      @click="advanceFromPage"
    >
      <article class="report-document" data-render-ready="true">
    <section class="report-page report-page--cover" :class="{ 'report-page--reader-hidden': !isContinuous && currentPage !== 0 }" data-reader-page="1" aria-label="报告封面">
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

    <section class="report-page report-page--intro" :class="{ 'report-page--reader-hidden': !isContinuous && currentPage !== 1 }" data-reader-page="2" aria-labelledby="report-intro-title">
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

    <section v-if="chapterItems.length" class="report-page report-page--toc" :class="{ 'report-page--reader-hidden': !isContinuous && currentPage !== 2 }" data-reader-page="3" aria-labelledby="report-toc-title">
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
      v-for="page in sectionPageEntries"
      :key="`${page.section.id}-reader-${page.pageInSection}`"
      class="report-page report-page--content"
      :class="{
        'report-page--foundation': page.section.kind === 'foundation',
        'report-page--markdown': page.section.kind === 'markdown',
        'report-page--reader-hidden': !isContinuous && currentPage !== page.pageIndex
      }"
      :data-reader-page="page.pageIndex + 1"
      :aria-labelledby="`report-section-title-${page.pageIndex}`"
    >
      <div class="report-page__running">
        <span>{{ chapterNumber(page.sectionIndex) }} · {{ page.section.title }}<template v-if="page.pageInSection"> · 续页 {{ page.pageInSection + 1 }}</template></span>
        <span>{{ reportIdentity }}</span>
      </div>
      <div class="report-page__body">
        <div class="report-heading">
          <span class="report-heading__prefix">{{ chapterNumber(page.sectionIndex) }}</span>
          <h2 :id="`report-section-title-${page.pageIndex}`">{{ page.section.title }}<template v-if="page.pageInSection">（续页 {{ page.pageInSection + 1 }}）</template></h2>
        </div>

        <p v-if="page.pageInSection === 0 && page.section.subtitle" class="report-lead">{{ page.section.subtitle }}</p>
        <div v-if="page.section.kind === 'markdown' && page.content" class="report-markdown-content" v-html="formatReportMarkdown(page.content)"></div>
        <div v-else-if="page.pageInSection === 0 && page.section.content" class="report-section-intro report-markdown-content" v-html="formatReportMarkdown(page.section.content)"></div>

        <div v-if="page.section.kind === 'foundation'" class="report-foundation-content">
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

        <ul v-if="page.pageInSection === 0 && page.section.items?.length" class="report-list report-list--spaced">
          <li v-for="(item, itemIndex) in page.section.items" :key="`${page.section.id}-item-${itemIndex}`">{{ item }}</li>
        </ul>
        <ReportContentBlock
          v-for="block in page.pageInSection === 0 ? page.section.blocks : []"
          :key="block.id"
          :block="block"
        />
      </div>
      <div class="report-page__footer"><span>{{ chapterNumber(page.sectionIndex) }} · {{ page.section.title }}<template v-if="page.pageInSection"> · 续页 {{ page.pageInSection + 1 }}</template></span></div>
    </section>

    <section v-if="hasSummary" class="report-page report-page--ending report-page--dark" :class="{ 'report-page--reader-hidden': !isContinuous && currentPage !== summaryPageIndex }" :data-reader-page="summaryPageIndex + 1" aria-labelledby="report-summary-title">
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

    <section v-if="!hasDocumentContent" class="report-page report-page--empty" :class="{ 'report-page--reader-hidden': !isContinuous && currentPage !== 2 }" data-reader-page="3" aria-live="polite">
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
    <p class="report-reader__hint" aria-hidden="true">{{ isContinuous ? '连续下滑阅读，也可使用左右方向键或目录跳转' : '点击报告页面或使用左右方向键翻页' }}</p>
    <span class="report-reader__live-status" role="status" aria-live="polite">第 {{ currentPage + 1 }} 页，共 {{ pageCount }} 页</span>
  </div>
</template>

<style src="../styles/report-document.css"></style>
<style src="../styles/report-reader.css"></style>
