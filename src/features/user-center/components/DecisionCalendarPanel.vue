<template>
  <section id="user-panel-calendar" class="content-section" role="tabpanel" aria-labelledby="user-tab-calendar" tabindex="0">
    <h3 class="section-title">决策日历</h3>
    <div class="calendar-access-card">
      <div class="calendar-access-mark" aria-hidden="true">辰</div>
      <div>
        <span class="calendar-access-kicker">PERSONAL TIMEZONE</span>
        <h4>把报告里的洞察带回每天</h4>
        <p>查看阶段行动节奏，记录真实发生的事</p>
      </div>
      <VanButton type="primary" native-type="button" class="btn-action" @click="$emit('open-calendar')">打开决策日历</VanButton>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'

export default {
  name: 'DecisionCalendarPanel',
  components: { VanButton },
  emits: ['open-calendar']
}
</script>

<style scoped src="../styles/calendar-panel.css"></style>
