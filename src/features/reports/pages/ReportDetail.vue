<template>
  <div class="report-detail">
    <BrandNav />

    <BrandPageHeader
      eyebrow="YOUR PERSONAL REPORT"
      :title="report ? '辰鉴 · 人生说明书' : loading ? '正在打开你的个人报告…' : loadError || '报告不存在或无权访问'"
      :description="report ? '从你的特质与处境出发，读懂反复出现的模式，也为下一步留一点新的可能。' : ''"
      seal="见己"
    >
      <template #leading>
        <VanButton type="default" plain native-type="button" class="btn-back" @click="goBack"><template #icon><IconMark name="arrow-left" /></template>返回</VanButton>
        <p v-if="staffView" class="report-meta">已交付最终报告 · 与用户收到的正文一致</p>
      </template>
      <template v-if="report" #default>
        <div class="report-meta">
          <span>生成日期：{{ report.basicInfo?.reportDate || '今天' }}</span>
          <span class="divider">|</span>
          <span>{{ report.basicInfo?.name || '用户' }}</span>
        </div>
      </template>
    </BrandPageHeader>

    <section class="report-content">
      <div class="container">
        <ReportContent
          v-if="report"
          :report="report"
          :foundation-data="foundationData"
          :content-without-foundation="contentWithoutFoundation"
        />

        <div v-if="report && !staffView" class="report-actions paper-card">
          <div class="report-next-copy"><p class="section-kicker">FROM INSIGHT TO ACTION</p><h2>把看见的，带回生活里</h2><p>用决策日历照看日常节奏，留下自己的行动与选择。</p></div>
          <VanButton type="primary" native-type="button" class="btn-action primary" @click="goToCalendar">
            <template #icon><IconMark class="icon" name="calendar" /></template>
            基于这份报告生成决策日历
          </VanButton>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'
import { getReportDetail } from '../api.js'
import ReportContent from '../components/ReportContent.vue'
import { normalizeReportData, parseLegacyReportContent } from '../report-content.js'
import { hasRole } from '../../../stores/auth'

export default {
  name: 'ReportDetail',
  components: { ReportContent, VanButton },
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
  computed: {
    staffView() { return hasRole('admin', 'consultant') }
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
      const requestId = Number(this.$route.query.request_id)
      if (this.staffView && Number.isSafeInteger(requestId) && requestId > 0) {
        this.$router.push({ path: '/staff', query: { request_id: String(requestId), section: 'overview' } })
      } else this.$router.go(-1)
    },
    goToCalendar() {
      const reportId = Number(this.$route.query.id)
      this.$router.push({
        path: '/pages/calendar/calendar',
        query: Number.isSafeInteger(reportId) && reportId > 0
          ? { generate: '1', source_report_id: String(reportId) }
          : { generate: '1' }
      })
    }
  }
}
</script>

<style scoped src="../styles/report-detail-base.css"></style>
<style scoped src="../styles/report-layout.css"></style>
<style scoped src="../styles/report-responsive-overrides.css"></style>
