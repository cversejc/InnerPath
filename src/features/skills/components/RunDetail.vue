<template>
  <section class="run-detail" aria-live="polite">
    <div class="panel-heading"><div><p class="eyebrow">RUN #{{ run.id }} / {{ run.status }}</p><h3>{{ run.status === 'FAILED' ? '执行失败' : run.status === 'COMPLETED' ? '执行结果' : '执行状态' }}</h3></div></div>
    <p v-if="run.error" class="run-error" role="alert">{{ run.error }}</p>
    <details v-if="run.context_snapshot && Object.keys(run.context_snapshot).length" class="context-reference">
      <summary>Skill 使用的上下文</summary>
      <pre class="output-block">{{ JSON.stringify(run.context_snapshot, null, 2) }}</pre>
    </details>
    <details class="context-reference">
      <summary>知识引用（{{ run.selected_knowledge?.length || 0 }}）</summary>
      <pre v-if="run.selected_knowledge?.length" class="output-block">{{ JSON.stringify(run.selected_knowledge, null, 2) }}</pre>
      <p v-else class="empty-reference">本次运行没有知识引用。</p>
    </details>
    <details class="context-reference">
      <summary>采用的 Examples（{{ run.selected_examples?.length || 0 }}）</summary>
      <div v-if="run.selected_examples?.length" class="selected-examples">
        <article v-for="example in run.selected_examples" :key="`${example.example_key}:${example.version_no}`" class="selected-example">
          <strong>Example #{{ example.example_id }} · v{{ example.version_no }}</strong>
          <span>匹配分 {{ example.retrieval_score }} · {{ example.retrieval_policy }}</span>
          <small>{{ example.selection_reasons?.join('、') || '已审核并匹配' }}</small>
          <pre class="output-block">{{ JSON.stringify(example.example_snapshot, null, 2) }}</pre>
        </article>
      </div>
      <p v-else class="empty-reference">本次运行没有采用已发布 Example。</p>
    </details>
    <form v-if="canRecommend" class="example-recommend-form" @submit.prevent="recommendExample">
      <h4>推荐为 Example</h4>
      <label for="recommend-example-type">示例类型</label>
      <select id="recommend-example-type" v-model="exampleType">
        <option value="POSITIVE">正向示例</option>
        <option value="CONTRASTIVE">对照示例</option>
        <option value="MISSED_INSIGHT">补充洞察</option>
      </select>
      <label for="recommend-example-tags">情境标签</label>
      <input id="recommend-example-tags" v-model="scenarioTags" placeholder="career, decision-making">
      <label for="recommend-example-points">教学要点（每行一项）</label>
      <textarea id="recommend-example-points" v-model="teachingPoints" rows="3"></textarea>
      <VanButton class="secondary-button compact-button" type="default" plain native-type="submit" :disabled="recommending" :loading="recommending">提交给管理员审核</VanButton>
      <p v-if="recommendationNotice" class="recommendation-notice" role="status">{{ recommendationNotice }}</p>
      <p v-if="recommendationError" class="run-error" role="alert">{{ recommendationError }}</p>
    </form>
    <template v-if="run.output_parsed">
      <h4>结构化输出</h4>
      <pre class="output-block">{{ JSON.stringify(run.output_parsed, null, 2) }}</pre>
      <details v-if="admin && run.output_raw" class="raw-output"><summary>原始输出</summary><pre class="output-block">{{ run.output_raw }}</pre></details>
    </template>
    <dl v-if="traceRows.length" class="trace-list"><div v-for="[label, value] in traceRows" :key="label"><dt>{{ label }}</dt><dd>{{ value }}</dd></div></dl>
  </section>
</template>

<script>
import { formatTrace } from '../studio.js'
import { Button as VanButton } from 'vant'
import api from '../api.js'

export default {
  name: 'RunDetail',
  components: { VanButton },
  props: {
    run: { type: Object, required: true },
    admin: { type: Boolean, default: false },
    caseId: { type: [String, Number], default: null }
  },
  data() {
    return {
      exampleType: 'POSITIVE',
      scenarioTags: '',
      teachingPoints: '',
      recommending: false,
      recommendationNotice: '',
      recommendationError: ''
    }
  },
  computed: {
    traceRows() {
      return formatTrace(this.run.model_trace)
    },
    canRecommend() {
      return !this.admin
        && this.caseId
        && Number(this.run.report_case_id) === Number(this.caseId)
        && this.run.status === 'COMPLETED'
    }
  },
  methods: {
    async recommendExample() {
      if (!this.canRecommend || this.recommending) return
      this.recommending = true
      this.recommendationError = ''
      this.recommendationNotice = ''
      try {
        const tags = this.scenarioTags.split(/[，,]/).map(item => item.trim()).filter(Boolean)
        const points = this.teachingPoints.split(/\r?\n/).map(item => item.trim()).filter(Boolean)
        const candidate = await api.recommendSkillExample(Number(this.caseId), {
          skill_run_id: this.run.id,
          example_type: this.exampleType,
          scenario_tags: tags,
          teaching_points: points
        })
        this.recommendationNotice = `已提交候选 Example #${candidate.id}，等待管理员审核。`
      } catch (error) {
        this.recommendationError = error.response?.data?.detail || '推荐提交失败。'
      } finally {
        this.recommending = false
      }
    }
  }
}
</script>

<style scoped src="./RunDetail.css"></style>
