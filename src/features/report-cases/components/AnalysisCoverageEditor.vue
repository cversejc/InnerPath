<template>
  <fieldset v-if="modelValue" class="review-coverage">
    <legend>{{ label }}</legend>
    <label>处理方式<select :value="modelValue.status" @change="set('status', $event.target.value)">
      <option value="FULFILLED">已完成分析</option><option value="DEFERRED">资料不足，暂缓并补问</option>
      <option v-if="!fields" value="NOT_APPLICABLE">有依据地说明不适用</option>
      <option v-if="modelValue.status === 'MISSING'" value="MISSING">待补全</option>
    </select></label>
    <label>处理理由<textarea :value="modelValue.reason" rows="2" @input="set('reason', $event.target.value)"></textarea></label>
    <label>覆盖依据摘句<textarea :value="modelValue.quote" rows="2" @input="set('quote', $event.target.value)"></textarea><small>请从当前分析正文中原样摘取一句。</small></label>
    <label>待补充问题<textarea :value="(modelValue.follow_up_questions || []).join('\n')" rows="2" @input="set('follow_up_questions', $event.target.value.split('\n').map(item => item.trim()).filter(Boolean))"></textarea><small>每行一个问题，资料不足时必须填写。</small></label>
    <template v-for="(description, key) in fields || {}" :key="key">
      <label v-if="key !== 'periods'">{{ description }}<textarea :value="modelValue.details?.[key] || ''" rows="2" @input="setDetail(key, $event.target.value)"></textarea></label>
      <div v-else>
        <article v-for="(period, index) in modelValue.details?.periods || []" :key="index" class="review-period">
          <strong>{{ period.start_year }}–{{ period.end_year }}</strong>
          <label v-for="(title, field) in periodFields" :key="field">{{ title }}<textarea :value="period[field]" rows="2" @input="setPeriod(index, field, $event.target.value)"></textarea></label>
          <VanButton plain native-type="button" @click="removePeriod(index)">移除此阶段</VanButton>
        </article>
        <label>添加程序计算中的阶段<select value="" @change="addPeriod($event.target.value)"><option value="">选择真实大运阶段</option><option v-for="(period, index) in sourcePeriods" :key="index" :value="String(index)">{{ period.start_year }}–{{ period.end_year }} · {{ period.pillar }}</option></select></label>
      </div>
    </template>
  </fieldset>
</template>
<script>
import { Button as VanButton } from 'vant'
import { cloneReviewValue } from '../analysis-review-flow.js'
export default {
  components: { VanButton },
  props: { modelValue: Object, label: String, fields: Object, sourcePeriods: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  data: () => ({ periodFields: { interaction: '原局与大运关系', theme: '阶段主题', capacity: '发展能力', old_pattern: '需要留意的旧模式' } }),
  methods: {
    set(key, value) { this.$emit('update:modelValue', { ...this.modelValue, [key]: value }) },
    setDetail(key, value) { this.set('details', { ...this.modelValue.details, [key]: value }) },
    setPeriod(index, field, value) {
      const periods = cloneReviewValue(this.modelValue.details?.periods || [])
      periods[index][field] = value
      this.setDetail('periods', periods)
    },
    addPeriod(index) {
      if (index === '' || !this.sourcePeriods[Number(index)]) return
      const source = this.sourcePeriods[Number(index)]
      const periods = this.modelValue.details?.periods || []
      if (periods.some(item => item.start_year === source.start_year && item.end_year === source.end_year)) return
      this.setDetail('periods', [...periods, { start_year: source.start_year, end_year: source.end_year, interaction: '', theme: '', capacity: '', old_pattern: '' }].sort((a, b) => a.start_year - b.start_year))
    },
    removePeriod(index) { this.setDetail('periods', (this.modelValue.details?.periods || []).filter((_, i) => i !== index)) }
  }
}
</script>
