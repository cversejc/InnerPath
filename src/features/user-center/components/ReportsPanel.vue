<template>
  <section id="user-panel-reports" class="content-section" role="tabpanel" aria-labelledby="user-tab-reports" tabindex="0">
    <div v-if="reports.length === 0" class="empty-state">
      <IconMark class="empty-icon" name="document" />
      <p>暂无报告</p>
      <VanButton type="primary" native-type="button" class="btn-action" @click="$emit('request-report')">申请说明书</VanButton>
    </div>
    <div v-else class="reports-list">
      <article
        v-for="report in reports"
        :key="report.id"
        class="report-card"
        :class="report.coverTheme ? `report-card--${report.coverTheme}` : ''"
      >
        <div class="report-cover">
          <span class="report-cover-seal" aria-hidden="true">辰</span>
          <header class="report-cover-heading">
            <h3>{{ report.title }}</h3>
            <span class="report-pillar-chip" :aria-label="`日柱 ${report.dayPillar}`">{{ report.dayPillar }}</span>
          </header>
          <span class="report-pillar-seal" aria-hidden="true">
            <span v-for="character in report.dayPillar" :key="character">{{ character }}</span>
          </span>
          <p class="report-summary">{{ report.description }}</p>
          <span v-if="report.isMock" class="report-demo-mark">演示样例</span>
          <div class="report-actions">
            <VanButton
              type="primary"
              native-type="button"
              class="btn-view"
              :disabled="report.isMock"
              :aria-label="report.isMock ? '演示样例报告，暂不可查看' : '查看报告'"
              @click="$emit('view-report', report.id)"
            >查看报告</VanButton>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'

export default {
  name: 'ReportsPanel',
  components: { VanButton },
  props: {
    reports: { type: Array, default: () => [] }
  },
  emits: ['request-report', 'view-report']
}
</script>

<style scoped src="../styles/reports.css"></style>
