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
      </template>
      <template v-if="report" #default>
        <div class="report-meta">
          <span>生成日期：{{ report.basicInfo?.reportDate || '今天' }}</span>
          <span class="divider">|</span>
          <span>{{ report.basicInfo?.name || '用户' }}</span>
        </div>
      </template>
      <template v-if="report" #actions>
        <div class="report-toolbar" aria-label="报告操作">
          <VanButton
            type="default"
            plain
            native-type="button"
            class="btn-print"
            :loading="downloadingPdf"
            :disabled="downloadingPdf"
            :loading-text="'正在生成…'"
            @click="downloadPdf"
          >
            <template v-if="!downloadingPdf" #icon><IconMark name="download" /></template>
            导出 PDF
          </VanButton>
          <p v-if="pdfError" class="report-toolbar__error" role="alert">{{ pdfError }}</p>
        </div>
      </template>
    </BrandPageHeader>

    <section class="report-content">
      <div class="container">
        <ReportContent v-if="reportDocument" :document="reportDocument" />

        <div v-if="report" class="report-actions paper-card">
          <div class="report-next-copy"><p class="section-kicker">FROM INSIGHT TO ACTION</p><h2>把看见的，带回生活里</h2><p>用决策日历照看日常节奏，留下自己的行动与选择。</p></div>
          <VanButton type="primary" native-type="button" class="btn-action primary" @click="goToCalendar">
            <template #icon><IconMark class="icon" name="calendar" /></template>
            打开决策日历
          </VanButton>
        </div>
      </div>
    </section>

    <BrandFooter />
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'
import BrandPageHeader from '../../../components/BrandPageHeader.vue'
import { downloadReportPdf, downloadReportPreviewPdf, getReportDetail } from '../api.js'
import ReportContent from '../components/ReportContent.vue'
import { normalizeReportData } from '../report-content.js'
import { createReportDocument } from '../report-document-model.js'
import { createReportPreview } from '../preview.js'

export default {
  name: 'ReportDetail',
  components: { BrandPageHeader, ReportContent, VanButton },
  data() {
    return {
      report: null,
      reportDocument: null,
      loading: true,
      loadError: '',
      downloadingPdf: false,
      pdfError: ''
    }
  },
  computed: {
    isPreviewReport() {
      return import.meta.env.DEV && this.$route.query.preview === '1'
    }
  },
  async mounted() {
    await this.loadReport()
  },
  methods: {
    async loadReport() {
      const reportId = this.$route.query.id
      try {
        if (import.meta.env.DEV && this.$route.query.preview === '1') {
          this.report = normalizeReportData(createReportPreview())
          this.reportDocument = createReportDocument(this.report)
          return
        }

        const reportData = await getReportDetail(reportId)
        this.report = normalizeReportData(reportData)
        this.reportDocument = createReportDocument(this.report)
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
    },
    async downloadPdf() {
      if (!this.report || this.downloadingPdf) return

      this.downloadingPdf = true
      this.pdfError = ''
      try {
        const response = this.isPreviewReport
          ? await downloadReportPreviewPdf(this.report)
          : await downloadReportPdf(this.$route.query.id)
        const filename = this.getPdfFilename(response.headers['content-disposition'])
        const url = window.URL.createObjectURL(response.data)
        const link = document.createElement('a')
        link.href = url
        link.download = filename || `人生说明书-${this.report.basicInfo?.name || '用户'}.pdf`
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
      } catch (error) {
        this.pdfError = error.response?.status === 404
          ? 'PDF 导出接口尚未部署，请更新后端服务后重试'
          : 'PDF 生成失败，请稍后重试'
      } finally {
        this.downloadingPdf = false
      }
    },
    getPdfFilename(contentDisposition = '') {
      const encodedName = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
      if (encodedName) {
        try {
          return decodeURIComponent(encodedName)
        } catch {
          return ''
        }
      }
      return contentDisposition.match(/filename="([^"]+)"/i)?.[1] || ''
    }
  }
}
</script>

<style scoped src="../styles/report-detail-base.css"></style>
<style scoped src="../styles/report-layout.css"></style>
<style scoped src="../styles/report-responsive-overrides.css"></style>
<style scoped src="../styles/report-document-shell.css"></style>
