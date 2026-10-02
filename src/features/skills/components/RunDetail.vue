<template>
  <section class="run-detail" aria-live="polite">
    <div class="panel-heading"><div><p class="eyebrow">RUN #{{ run.id }} / {{ run.status }}</p><h3>{{ run.status === 'FAILED' ? '执行失败' : run.status === 'COMPLETED' ? '执行结果' : '执行状态' }}</h3></div></div>
    <p v-if="run.error" class="run-error" role="alert">{{ run.error }}</p>
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

export default {
  name: 'RunDetail',
  props: {
    run: { type: Object, required: true },
    admin: { type: Boolean, default: false }
  },
  computed: {
    traceRows() {
      return formatTrace(this.run.model_trace)
    }
  }
}
</script>

<style scoped src="./RunDetail.css"></style>
