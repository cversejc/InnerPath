<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Button as VanButton } from 'vant'

const props = defineProps({ sections: { type: Array, required: true } })
const opened = ref(new Set([0]))
const sectionElements = new Map()
const chapters = computed(() => props.sections.map((section, index) => ({
  ...section,
  index,
  label: section.title || section.section_title || `第 ${index + 1} 节`,
  group: section.section_title || chapterGroup(section.fragment_key)
})))

function chapterGroup(key = '') {
  if (key.startsWith('report.blocks.')) return '卡在哪'
  if (key.startsWith('report.direction.')) return '往哪去'
  if (key === 'report.ending') return '带回日常'
  return '你是谁'
}

watch(() => props.sections, () => { opened.value = new Set([0]) })

function trackToggle(index, event) {
  const next = new Set(opened.value)
  if (event.target.open) next.add(index)
  else next.delete(index)
  opened.value = next
}

async function openChapter(index) {
  opened.value = new Set([...opened.value, index])
  await nextTick()
  const target = sectionElements.get(index)
  target?.scrollIntoView({ block: 'start' })
  target?.querySelector('summary')?.focus({ preventScroll: true })
}
</script>

<template>
  <div class="chapter-reader">
    <nav class="reader-directory" aria-label="报告章节目录">
      <details>
        <summary>章节目录 · 共 {{ chapters.length }} 节</summary>
        <ol>
          <li v-for="chapter in chapters" :key="chapter.index">
            <button type="button" :aria-controls="`report-chapter-${chapter.index}`" @click="openChapter(chapter.index)">
              <span class="chapter-group">{{ chapter.group }}</span>
              {{ chapter.label }}
            </button>
          </li>
        </ol>
      </details>
      <div class="reader-controls">
        <span role="status">已展开 {{ opened.size }} / {{ chapters.length }} 节</span>
        <div>
          <VanButton plain native-type="button" @click="opened = new Set(chapters.map(chapter => chapter.index))">展开全部</VanButton>
          <VanButton plain native-type="button" @click="opened = new Set()">收起全部</VanButton>
        </div>
      </div>
    </nav>

    <details
      v-for="chapter in chapters"
      :id="`report-chapter-${chapter.index}`"
      :key="chapter.index"
      :ref="element => element ? sectionElements.set(chapter.index, element) : sectionElements.delete(chapter.index)"
      class="reader-chapter"
      :open="opened.has(chapter.index)"
      @toggle="trackToggle(chapter.index, $event)"
    >
      <summary>
        <span class="chapter-group">{{ chapter.group }} · {{ chapter.index + 1 }}</span>
        <h2>{{ chapter.label }}</h2>
      </summary>
      <p class="chapter-prose">{{ chapter.content }}</p>
    </details>
  </div>
</template>

<style scoped>
.chapter-reader { display: grid; gap: var(--space-4); }
.reader-directory,
.reader-chapter { background: var(--paper-soft); border: 1px solid var(--line); border-radius: var(--radius-card); padding: var(--space-5); }
.reader-directory summary { font-family: var(--font-ui); font-weight: var(--weight-semibold); min-height: var(--touch-target); }
summary { cursor: pointer; }
summary:focus-visible,
.reader-directory button:focus-visible { outline: 2px solid var(--cinnabar-deep); outline-offset: 4px; }
.reader-directory ol { padding-left: var(--space-5); margin: var(--space-2) 0 var(--space-4); }
.reader-directory button { width: 100%; min-height: var(--touch-target); border: 0; background: transparent; color: var(--ink); padding: var(--space-2); text-align: left; font-family: var(--font-ui); font-size: var(--text-body); line-height: var(--leading-ui); cursor: pointer; }
.reader-directory button:hover { background: var(--paper); }
.chapter-group { display: block; margin-bottom: var(--space-2); font-family: var(--font-ui); font-size: var(--text-body-sm); font-weight: var(--weight-medium); color: var(--gold-deep); }
.reader-controls { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--space-3); color: var(--ink-soft); font-size: var(--text-body-sm); }
.reader-controls > div { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.reader-chapter { scroll-margin-top: calc(var(--space-7) + var(--space-5)); }
.reader-chapter summary { position: relative; padding-right: var(--space-5); list-style: none; }
.reader-chapter summary::-webkit-details-marker { display: none; }
.reader-chapter summary::after { position: absolute; right: 0; top: var(--space-2); content: '+'; color: var(--cinnabar-deep); font-size: var(--text-h3); }
.reader-chapter[open] summary::after { content: '−'; }
.reader-chapter h2 { margin: 0; color: var(--ink); font-family: var(--font-display); font-size: var(--text-h2); font-weight: var(--weight-medium); line-height: var(--leading-heading); overflow-wrap: anywhere; }
.chapter-prose { margin: var(--space-5) 0 0; border-top: 1px solid var(--line); padding-top: var(--space-5); font-family: var(--font-body); font-size: var(--text-body); line-height: var(--leading-prose); white-space: pre-line; overflow-wrap: anywhere; }
@media (max-width: 480px) {
  .reader-directory,
  .reader-chapter { padding: var(--space-4); }
}
</style>
