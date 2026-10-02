<template>
  <section class="examples-panel">
    <div class="examples-toolbar">
      <div>
        <p class="eyebrow">EXAMPLE LIBRARY</p>
        <h2>{{ admin ? 'Example 审核' : '已发布 Examples' }}</h2>
      </div>
      <div v-if="admin" class="examples-filters">
        <label for="example-status">状态</label>
        <select id="example-status" v-model="filter" @change="loadExamples">
          <option value="">全部</option>
          <option value="CANDIDATE">待审核</option>
          <option value="PUBLISHED">已发布</option>
          <option value="RETIRED">已退役</option>
        </select>
        <VanButton class="secondary-button compact-button" type="default" plain :disabled="loading" @click="loadExamples">刷新</VanButton>
      </div>
    </div>

    <p v-if="error" class="examples-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="examples-notice" role="status">{{ notice }}</p>

    <div class="examples-layout">
      <div class="examples-list" aria-label="Example 列表">
        <button
          v-for="example in examples"
          :key="example.id"
          type="button"
          class="example-row"
          :class="{ selected: selected?.id === example.id }"
          @click="selectExample(example)"
        >
          <span class="example-row-main">
            <strong>{{ example.skill_key }}<template v-if="example.target_fragment_key"> · {{ example.target_fragment_key }}</template></strong>
            <small>Example #{{ example.id }} · v{{ example.version_no }} · {{ example.scenario_tags?.join('、') || '未分类' }}</small>
          </span>
          <span class="version-state" :class="`state-${example.status.toLowerCase()}`">{{ statusLabel(example.status) }}</span>
        </button>
        <p v-if="!loading && !examples.length" class="examples-empty">{{ admin ? '当前筛选没有 Example。' : '暂无已发布 Example。' }}</p>
      </div>

      <form v-if="selected" class="example-editor" @submit.prevent="saveCandidate">
        <div class="example-editor-heading">
          <div><p class="eyebrow">EXAMPLE #{{ selected.id }} / V{{ selected.version_no }}</p><h3>{{ selected.skill_key }}</h3></div>
          <span class="version-state" :class="`state-${selected.status.toLowerCase()}`">{{ statusLabel(selected.status) }}</span>
        </div>
        <dl class="example-source">
          <div><dt>来源 Case</dt><dd>{{ selected.source_case_id || '—' }}</dd></div>
          <div><dt>来源 SkillRun</dt><dd>{{ selected.source_skill_run_id || '—' }}</dd></div>
          <div><dt>审核人</dt><dd>{{ selected.reviewed_by || '未审核' }}</dd></div>
        </dl>

        <template v-if="admin && selected.status === 'CANDIDATE'">
          <label for="example-fragment">目标片段</label>
          <input id="example-fragment" v-model.trim="draft.target_fragment_key" maxlength="200">
          <label for="example-tags">情境标签</label>
          <input id="example-tags" v-model="draft.scenarioTags" placeholder="career, decision-making">
          <label for="example-applicability">适用条件 JSON</label>
          <textarea id="example-applicability" v-model="draft.applicability" rows="3" spellcheck="false"></textarea>
          <label for="example-input">脱敏输入情境 JSON</label>
          <textarea id="example-input" v-model="draft.inputContext" rows="5" spellcheck="false"></textarea>
          <label for="example-output">期望输出 JSON</label>
          <textarea id="example-output" v-model="draft.expectedOutput" rows="6" spellcheck="false"></textarea>
          <label for="example-teaching">教学要点（每行一项）</label>
          <textarea id="example-teaching" v-model="draft.teachingPoints" rows="3"></textarea>
          <label for="example-anti-patterns">反例模式（每行一项）</label>
          <textarea id="example-anti-patterns" v-model="draft.antiPatterns" rows="3"></textarea>
          <div class="example-review-fields">
            <label for="example-quality">质量评分</label>
            <input id="example-quality" v-model.number="draft.qualityScore" type="number" min="0" max="1" step="0.01" required>
            <label class="deidentification-check"><input v-model="draft.deidentified" type="checkbox"> 已完成人工脱敏复核</label>
          </div>
          <div class="example-actions">
            <VanButton class="secondary-button compact-button" type="default" plain :disabled="busy" native-type="submit" :loading="busy">保存审核内容</VanButton>
            <VanButton class="primary-button compact-button" type="primary" :disabled="busy || !selected.deidentified || selected.quality_score < 0.6 || !selected.teaching_points?.length" :loading="busy" @click.prevent="publishSelected">审核并发布</VanButton>
          </div>
        </template>

        <template v-else>
          <div class="example-readonly-block"><strong>教学要点</strong><ul><li v-for="(point, index) in selected.teaching_points" :key="index">{{ point }}</li></ul></div>
          <div class="example-readonly-block"><strong>适用条件</strong><pre>{{ JSON.stringify(selected.applicability_json || {}, null, 2) }}</pre></div>
          <div class="example-readonly-block"><strong>期望输出</strong><pre>{{ JSON.stringify(selected.expected_output || {}, null, 2) }}</pre></div>
          <div v-if="admin" class="example-actions">
            <VanButton v-if="selected.status === 'PUBLISHED' || selected.status === 'RETIRED'" class="secondary-button compact-button" type="default" plain :disabled="busy" @click="createRevision">创建新版本</VanButton>
            <VanButton v-if="selected.status !== 'RETIRED'" class="secondary-button compact-button" type="default" plain :disabled="busy" @click="retireSelected">退役</VanButton>
          </div>
        </template>
      </form>
      <div v-else class="example-editor-empty">选择一条 Example 查看审核信息。</div>
    </div>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import api from '../api.js'

function lines(value) {
  return value.split(/\r?\n/).map(item => item.trim()).filter(Boolean)
}

function emptyDraft() {
  return {
    target_fragment_key: '',
    scenarioTags: '',
    applicability: '{}',
    inputContext: '{}',
    expectedOutput: '{}',
    teachingPoints: '',
    antiPatterns: '',
    qualityScore: 0.8,
    deidentified: false
  }
}

export default {
  name: 'ExamplesPanel',
  components: { VanButton },
  props: {
    admin: { type: Boolean, default: true },
    skillKey: { type: String, default: '' }
  },
  data() {
    return {
      examples: [],
      selected: null,
      filter: 'CANDIDATE',
      loading: false,
      busy: false,
      error: '',
      notice: '',
      draft: emptyDraft()
    }
  },
  mounted() {
    this.loadExamples()
  },
  watch: {
    skillKey() {
      this.loadExamples()
    }
  },
  methods: {
    async loadExamples() {
      this.loading = true
      this.error = ''
      try {
        if (this.admin) {
          const params = { status: this.filter || undefined, skill_key: this.skillKey || undefined }
          this.examples = await api.getSkillExamples(params)
        } else {
          this.examples = await api.getPublishedSkillExamples({ skill_key: this.skillKey || undefined })
        }
        if (this.selected) {
          const refreshed = this.examples.find(item => item.id === this.selected.id)
          this.selected = refreshed || null
          if (this.selected) this.selectExample(this.selected)
        }
      } catch (error) {
        this.error = error.response?.data?.detail || '无法读取 Examples。'
      } finally {
        this.loading = false
      }
    },
    selectExample(example) {
      this.selected = example
      this.notice = ''
      this.draft = {
        target_fragment_key: example.target_fragment_key || '',
        scenarioTags: (example.scenario_tags || []).join(', '),
        applicability: JSON.stringify(example.applicability_json || {}, null, 2),
        inputContext: JSON.stringify(example.input_context || {}, null, 2),
        expectedOutput: JSON.stringify(example.expected_output || {}, null, 2),
        teachingPoints: (example.teaching_points || []).join('\n'),
        antiPatterns: (example.anti_patterns || []).join('\n'),
        qualityScore: example.quality_score ?? 0.8,
        deidentified: Boolean(example.deidentified)
      }
    },
    parseObject(text, label) {
      let value
      try {
        value = JSON.parse(text)
      } catch (error) {
        throw new Error(`${label} JSON 格式错误：${error.message}`)
      }
      if (!value || Array.isArray(value) || typeof value !== 'object') {
        throw new Error(`${label} 必须是 JSON 对象。`)
      }
      return value
    },
    async saveCandidate() {
      if (!this.admin || !this.selected) return
      this.busy = true
      this.error = ''
      try {
        const updated = await api.updateSkillExample(this.selected.id, {
          target_fragment_key: this.draft.target_fragment_key || null,
          scenario_tags: this.draft.scenarioTags.split(/[，,]/).map(item => item.trim()).filter(Boolean),
          applicability_json: this.parseObject(this.draft.applicability, '适用条件'),
          input_context: this.parseObject(this.draft.inputContext, '输入情境'),
          expected_output: this.parseObject(this.draft.expectedOutput, '期望输出'),
          teaching_points: lines(this.draft.teachingPoints),
          anti_patterns: lines(this.draft.antiPatterns),
          quality_score: Number(this.draft.qualityScore),
          confirmed_deidentified: this.draft.deidentified
        })
        this.replaceExample(updated)
        this.notice = '审核内容已保存。'
      } catch (error) {
        this.error = error.response?.data?.detail || error.message || '保存失败。'
      } finally {
        this.busy = false
      }
    },
    async publishSelected() {
      if (!this.selected) return
      await this.saveCandidate()
      if (this.error) return
      this.busy = true
      try {
        const published = await api.publishSkillExample(this.selected.id)
        this.replaceExample(published)
        this.notice = `Example v${published.version_no} 已发布。`
        await this.loadExamples()
      } catch (error) {
        this.error = error.response?.data?.detail || '发布失败。'
      } finally {
        this.busy = false
      }
    },
    async retireSelected() {
      if (!this.selected) return
      this.busy = true
      try {
        const retired = await api.retireSkillExample(this.selected.id)
        this.replaceExample(retired)
        this.notice = 'Example 已退役。'
        await this.loadExamples()
      } catch (error) {
        this.error = error.response?.data?.detail || '退役失败。'
      } finally {
        this.busy = false
      }
    },
    async createRevision() {
      if (!this.selected) return
      this.busy = true
      try {
        const candidate = await api.createSkillExampleRevision(this.selected.id)
        await this.loadExamples()
        this.filter = 'CANDIDATE'
        this.examples = await api.getSkillExamples({
          status: 'CANDIDATE',
          skill_key: this.skillKey || undefined
        })
        this.selectExample(candidate)
        this.notice = `已创建 Example v${candidate.version_no} 待审版本。`
      } catch (error) {
        this.error = error.response?.data?.detail || '创建新版本失败。'
      } finally {
        this.busy = false
      }
    },
    replaceExample(example) {
      this.selected = example
      this.examples = this.examples.map(item => item.id === example.id ? example : item)
      this.selectExample(example)
    },
    statusLabel(status) {
      return { CANDIDATE: '待审核', PUBLISHED: '已发布', RETIRED: '已退役' }[status] || status
    }
  }
}
</script>

<style scoped src="./ExamplesPanel.css"></style>
