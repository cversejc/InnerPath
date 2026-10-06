<script setup>
defineProps({
  eyebrow: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  seal: { type: String, default: '见己' },
  contained: { type: Boolean, default: false },
  compact: { type: Boolean, default: false }
})
</script>

<template>
  <header class="brand-page-header" :class="{ 'is-contained': contained, 'is-compact': compact }">
    <div class="container brand-page-header-inner">
      <div class="brand-page-copy">
        <div v-if="$slots.leading" class="brand-page-leading"><slot name="leading" /></div>
        <p class="section-kicker">{{ eyebrow }}</p>
        <h1>{{ title }}</h1>
        <span class="brand-page-rule" aria-hidden="true"></span>
        <p v-if="description" class="brand-page-description">{{ description }}</p>
        <div v-if="$slots.default" class="brand-page-meta"><slot /></div>
      </div>
      <div class="brand-page-margin" aria-hidden="true">
        <span class="brand-page-seal">{{ seal }}</span>
        <span class="brand-page-motto">见自己 · 知其序 · 行其路</span>
      </div>
      <div v-if="$slots.actions" class="brand-page-actions"><slot name="actions" /></div>
    </div>
  </header>
</template>

<style scoped src="./BrandPageHeader.css"></style>
