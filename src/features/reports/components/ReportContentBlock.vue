<script setup>
import { computed } from 'vue'
import { formatReportMarkdown } from '../report-markdown.js'

defineOptions({ name: 'ReportContentBlock' })

const props = defineProps({
  block: { type: Object, required: true }
})

const headingTag = computed(() => `h${Math.min(5, 3 + Math.max(0, Number(props.block.depth) || 0))}`)
const blockClass = computed(() => `report-content-block--${props.block.displayType || 'prose'}`)
const depthClass = computed(() => `report-content-block--depth-${Math.min(3, Math.max(0, Number(props.block.depth) || 0))}`)
</script>

<template>
  <section
    class="report-content-block"
    :class="[blockClass, depthClass, { 'report-content-block--untitled': !block.title, 'report-content-block--continued': block.continued }]"
    :id="block.anchorId"
  >
    <component :is="headingTag" v-if="block.title" class="report-content-block__title" :class="`report-content-block__title--${headingTag}`">
      {{ block.title }}<span v-if="block.continued" class="report-content-block__continued-label">（续）</span>
    </component>
    <p v-if="block.subtitle" class="report-content-block__subtitle">{{ block.subtitle }}</p>
    <div v-if="block.comparison?.from || block.comparison?.to" class="report-comparison">
      <div class="report-comparison__side">
        <span>{{ block.comparison.fromLabel }}</span>
        <p>{{ block.comparison.from }}</p>
      </div>
      <span class="report-comparison__arrow" aria-hidden="true">→</span>
      <div class="report-comparison__side">
        <span>{{ block.comparison.toLabel }}</span>
        <p>{{ block.comparison.to }}</p>
      </div>
    </div>
    <blockquote v-else-if="block.content && block.displayType === 'quote'" class="report-content-block__quote report-markdown-content" v-html="formatReportMarkdown(block.content)"></blockquote>
    <aside v-else-if="block.content && block.displayType === 'takeaway'" class="report-content-block__takeaway report-markdown-content" v-html="formatReportMarkdown(block.content)"></aside>
    <div v-else-if="block.content" class="report-content-block__content report-markdown-content" v-html="formatReportMarkdown(block.content)"></div>
    <dl v-if="block.metadata?.length" class="report-content-block__metadata">
      <template v-for="(item, index) in block.metadata" :key="`${block.id}-meta-${index}`">
        <dt>{{ item.label }}</dt>
        <dd>{{ item.value }}</dd>
      </template>
    </dl>
    <ul v-if="block.items?.length" class="report-list report-list--spaced" :class="{ 'report-list--tags': block.displayType === 'tags', 'report-list--checklist': block.displayType === 'checklist' }">
      <li v-for="(item, index) in block.items" :key="`${block.id}-item-${index}`">{{ item }}</li>
    </ul>
    <ReportContentBlock
      v-for="child in block.children"
      :key="child.id"
      :block="child"
    />
  </section>
</template>
