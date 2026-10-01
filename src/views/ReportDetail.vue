<template>
  <div class="report-detail">
    <BrandNav />

    <section v-if="report" class="report-header">
      <div class="container">
        <button class="btn-back" type="button" @click="goBack"><IconMark name="arrow-left" />返回</button>
        <h1>辰鉴·人生说明书</h1>
        <div class="report-meta">
          <span>生成日期：{{ report.basicInfo?.reportDate || '今天' }}</span>
          <span class="divider">|</span>
          <span>{{ report.basicInfo?.name || '用户' }}</span>
        </div>
      </div>
    </section>

    <section v-else-if="loading" class="report-header">
      <div class="container"><h1>正在打开你的个人报告…</h1></div>
    </section>
    <section v-else class="report-header">
      <div class="container">
        <button class="btn-back" type="button" @click="goBack"><IconMark name="arrow-left" />返回</button>
        <h1>{{ loadError || '报告不存在或无权访问' }}</h1>
      </div>
    </section>

    <section class="report-content">
      <div class="container">
        <ReportContent
          v-if="report"
          :report="report"
          :foundation-data="foundationData"
          :content-without-foundation="contentWithoutFoundation"
        />

        <div class="report-actions">
          <button class="btn-action primary" type="button" @click="goToCalendar">
            <IconMark class="icon" name="calendar" />
            打开决策日历
          </button>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { getReportDetail } from '../utils/aiService.js'
import ReportContent from '../features/reports/components/ReportContent.vue'
import { normalizeReportData, parseLegacyReportContent } from '../features/reports/report-content.js'

export default {
  name: 'ReportDetail',
  components: { ReportContent },
  data() {
    return {
      report: null,
      foundationData: null,
      contentWithoutFoundation: '',
      loading: true,
      loadError: ''
    }
  },
  async mounted() {
    await this.loadReport()
  },
  methods: {
    async loadReport() {
      const reportId = this.$route.query.id
      try {
        const reportData = await getReportDetail(reportId)
        this.report = normalizeReportData(reportData)
        if (this.report.contentPayload?.foundation_data) {
          this.foundationData = this.report.contentPayload.foundation_data
        } else if (this.report.aiGeneratedContent) {
          const parsed = parseLegacyReportContent(this.report.aiGeneratedContent)
          this.foundationData = parsed.foundationData
          this.contentWithoutFoundation = parsed.contentWithoutFoundation
        }
      } catch (error) {
        this.loadError = error.response?.status === 403 ? '你没有权限查看这份报告' : '报告不存在或加载失败'
      } finally {
        this.loading = false
      }
    },
    goBack() {
      this.$router.go(-1)
    },
    goToCalendar() {
      this.$router.push('/pages/calendar/calendar')
    }
  }
}
</script>

<style scoped src="../features/reports/styles/report-detail-base.css"></style>
<style scoped src="../features/reports/styles/report-layout.css"></style>
<style scoped src="../features/reports/styles/report-responsive-overrides.css"></style>
