<template>
  <section id="user-panel-reports" class="content-section" role="tabpanel" aria-labelledby="user-tab-reports" tabindex="0">
    <h3 class="section-title">报告</h3>
    <div v-if="reports.length === 0" class="empty-state">
      <IconMark class="empty-icon" name="document" />
      <p>暂无报告</p>
      <VanButton type="primary" native-type="button" class="btn-action" @click="$emit('request-report')">申请说明书</VanButton>
    </div>
    <div v-else class="reports-list">
      <article v-for="report in reports" :key="report.id" class="report-card">
        <div class="report-header">
          <h4>{{ report.title }}</h4>
          <span class="report-date">{{ report.date }}</span>
        </div>
        <div class="report-preview">
          <div class="preview-item"><strong>个人属性：</strong>{{ report.energyType }}</div>
          <div class="preview-item"><strong>核心特质：</strong>{{ report.coreTraits }}</div>
        </div>
        <div class="report-actions">
          <VanButton type="primary" native-type="button" class="btn-view" @click="$emit('view-report', report.id)">查看完整报告</VanButton>
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
