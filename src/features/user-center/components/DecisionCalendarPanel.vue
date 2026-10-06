<template>
  <section id="user-panel-calendar" class="content-section" role="tabpanel" aria-labelledby="user-tab-calendar" tabindex="0">
    <article class="calendar-access-card" :class="season ? `calendar-access-card--${season}` : ''">
      <div class="calendar-access-cover">
        <span class="calendar-access-mark" aria-hidden="true">辰</span>
        <header class="calendar-access-heading">
          <h3>{{ title }}</h3>
        </header>
        <p class="calendar-access-quote">{{ quote }}</p>
        <div class="calendar-access-actions">
          <VanButton type="primary" native-type="button" class="btn-action" @click="$emit('open-calendar')">打开决策日历</VanButton>
        </div>
      </div>
    </article>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'

export default {
  name: 'DecisionCalendarPanel',
  components: { VanButton },
  props: {
    title: { type: String, default: '辰鉴·决策日历' },
    quote: { type: String, default: '为重要的选择留出从容，也为下一步留一点余地。' },
    season: { type: String, default: 'spring' }
  },
  emits: ['open-calendar']
}
</script>

<style scoped src="../styles/calendar-panel.css"></style>
