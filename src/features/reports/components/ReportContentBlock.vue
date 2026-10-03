<script setup>
import { formatReportMarkdown } from '../report-markdown.js'

defineOptions({ name: 'ReportContentBlock' })

defineProps({
  block: { type: Object, required: true }
})
</script>

<template>
  <section class="report-content-block" :class="{ 'report-content-block--untitled': !block.title }">
    <h3 v-if="block.title" class="report-content-block__title">{{ block.title }}</h3>
    <p v-if="block.subtitle" class="report-content-block__subtitle">{{ block.subtitle }}</p>
    <div v-if="block.content" class="report-content-block__content report-markdown-content" v-html="formatReportMarkdown(block.content)"></div>
    <ul v-if="block.items?.length" class="report-list report-list--spaced">
      <li v-for="(item, index) in block.items" :key="`${block.id}-item-${index}`">{{ item }}</li>
    </ul>
    <ReportContentBlock
      v-for="child in block.children"
      :key="child.id"
      :block="child"
    />
  </section>
</template>
