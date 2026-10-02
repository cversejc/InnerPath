<template>
  <div class="skill-studio-shell">
    <BrandNav />
    <main class="skill-studio-main">
      <header class="studio-heading">
        <div>
          <p class="section-kicker">AI PRODUCTION / SKILL STUDIO</p>
          <h1>Skill Studio</h1>
          <p v-if="!isAdmin && caseId">Case #{{ caseId }}</p>
        </div>
        <div class="studio-heading-actions">
          <router-link class="secondary-button compact-button" :to="isAdmin ? '/admin' : '/staff'">返回工作台</router-link>
          <VanButton v-if="isAdmin" class="secondary-button compact-button" type="default" plain :disabled="loading" @click="loadVersions">刷新</VanButton>
        </div>
      </header>

      <p v-if="message" class="studio-message" :class="{ error: messageKind === 'error' }" role="status" aria-live="polite">{{ message }}</p>

      <template v-if="isAdmin">
        <nav class="studio-tabs" aria-label="Skill Studio">
          <button type="button" role="tab" :aria-selected="activeAdminTab === 'skills'" :class="{ selected: activeAdminTab === 'skills' }" @click="activeAdminTab = 'skills'">Skills</button>
          <button type="button" role="tab" :aria-selected="activeAdminTab === 'examples'" :class="{ selected: activeAdminTab === 'examples' }" @click="activeAdminTab = 'examples'">Examples</button>
          <button type="button" role="tab" :aria-selected="activeAdminTab === 'evaluation'" :class="{ selected: activeAdminTab === 'evaluation' }" @click="activeAdminTab = 'evaluation'">Evaluation</button>
        </nav>

        <template v-if="activeAdminTab === 'skills'">
        <section class="studio-toolbar" aria-label="技能版本">
          <div class="version-heading"><div><p class="eyebrow">VERSIONS</p><h2>Skill 版本</h2></div><VanButton class="primary-button compact-button" type="primary" :disabled="saving || !selectedVersion" :loading="saving" @click="createDraft">从当前版本创建草稿</VanButton></div>
          <div class="version-list" role="list">
            <button v-for="version in versions" :key="version.id" type="button" role="listitem" class="version-row" :class="{ selected: selectedVersion?.id === version.id }" @click="selectVersion(version)">
              <span><strong>{{ version.name }}</strong><small>{{ version.skill_key }} · v{{ version.version }}</small></span>
              <span class="version-state" :class="`state-${version.status.toLowerCase()}`">{{ VERSION_STATUS_LABELS[version.status] || version.status }}</span>
            </button>
            <p v-if="!loading && !versions.length" class="empty-line">暂无 Skill 版本。</p>
          </div>
        </section>

        <section v-if="selectedVersion" class="studio-grid">
          <div class="studio-editor">
            <div class="panel-heading"><div><p class="eyebrow">SPECIFICATION / V{{ selectedVersion.version }}</p><h2>{{ selectedVersion.name }}</h2></div><span class="version-state" :class="`state-${selectedVersion.status.toLowerCase()}`">{{ VERSION_STATUS_LABELS[selectedVersion.status] }}</span></div>
            <label class="json-label" for="skill-specification">Skill 配置</label>
            <textarea id="skill-specification" v-model="specificationText" class="json-editor" :readonly="!editable" spellcheck="false"></textarea>
            <p v-if="specError" class="field-error" role="alert">{{ specError }}</p>
            <div class="editor-actions">
              <VanButton v-if="editable" class="secondary-button compact-button" type="default" plain :disabled="saving || !specificationText.trim() || Boolean(specError)" :loading="saving" @click="saveDraft">保存草稿</VanButton>
              <VanButton v-if="editable" class="primary-button compact-button" type="primary" :disabled="saving || publishing || Boolean(specError) || selectedVersion.status !== 'DRAFT'" :loading="publishing" @click="publish">发布版本</VanButton>
            </div>
          </div>

          <aside class="studio-run-panel">
            <div class="panel-heading"><div><p class="eyebrow">DEBUG RUN</p><h2>试运行</h2></div></div>
            <label class="json-label" for="skill-input">输入快照</label>
            <textarea id="skill-input" v-model="inputText" class="json-editor input-editor" spellcheck="false"></textarea>
            <label class="json-label" for="skill-instruction">本次附加指令</label>
            <textarea id="skill-instruction" v-model.trim="runtimeInstruction" class="instruction-input" maxlength="4000" rows="3" placeholder="可留空"></textarea>
            <p v-if="inputError" class="field-error" role="alert">{{ inputError }}</p>
            <VanButton class="primary-button run-button" type="primary" :disabled="running || selectedVersion.status === 'RETIRED'" :loading="running" @click="startRun">{{ running ? '已加入运行队列' : '运行 Skill' }}</VanButton>
          </aside>
        </section>

        <section v-if="selectedVersion" class="runs-section">
          <div class="panel-heading"><div><p class="eyebrow">RUNS / ISSUES</p><h2>运行记录与问题</h2></div><span>{{ runs.length }} 条</span></div>
          <div class="runs-layout">
            <div class="run-list">
              <button v-for="run in runs" :key="run.id" type="button" class="run-row" :class="{ selected: selectedRun?.id === run.id }" @click="selectRun(run)">
                <span><strong>Run #{{ run.id }}</strong><small>{{ formatDate(run.created_at) }} · {{ run.model_trace?.model || '等待执行' }}</small></span>
                <span class="version-state" :class="`state-${run.status.toLowerCase()}`">{{ RUN_STATUS_LABELS[run.status] || run.status }}</span>
              </button>
              <p v-if="!runs.length" class="empty-line">该版本还没有运行记录。</p>
            </div>
            <RunDetail v-if="selectedRun" :run="selectedRun" :admin="true" />
            <div v-else class="run-detail-empty">暂无选中的运行记录。</div>
          </div>
        </section>
        </template>

        <ExamplesPanel v-else-if="activeAdminTab === 'examples'" :admin="true" :skill-key="selectedVersion?.skill_key || ''" />
        <EvaluationPanel
          v-else
          :version="selectedVersion"
          :start-evaluation="startEvaluation"
        />
      </template>

      <template v-else>
        <section class="consultant-case-lookup" aria-label="报告 Case">
          <form @submit.prevent="loadCaseRuns">
            <label for="case-id">已分配报告 Case 编号</label>
            <input id="case-id" v-model.trim="caseIdDraft" type="number" min="1" required>
            <VanButton class="primary-button compact-button" type="primary" native-type="submit" :disabled="caseLoading" :loading="caseLoading">查看运行结果</VanButton>
          </form>
        </section>
        <section v-if="caseId" class="runs-section">
          <div class="panel-heading"><div><p class="eyebrow">ASSIGNED CASE / #{{ caseId }}</p><h2>Skill 运行结果</h2></div><span>{{ runs.length }} 条</span></div>
          <div class="runs-layout">
            <div class="run-list">
              <button v-for="run in runs" :key="run.id" type="button" class="run-row" :class="{ selected: selectedRun?.id === run.id }" @click="selectRun(run)">
                <span><strong>{{ run.target_key || run.target_type }} · Run #{{ run.id }}</strong><small>{{ formatDate(run.created_at) }} · {{ run.model_trace?.model || '等待执行' }}</small></span>
                <span class="version-state" :class="`state-${run.status.toLowerCase()}`">{{ RUN_STATUS_LABELS[run.status] || run.status }}</span>
              </button>
              <p v-if="!runs.length" class="empty-line">该 Case 暂无 Skill 运行记录。</p>
            </div>
            <RunDetail v-if="selectedRun" :run="selectedRun" :admin="false" :case-id="caseId" />
            <div v-else class="run-detail-empty">暂无选中的运行记录。</div>
          </div>
        </section>
        <section class="published-example-section">
          <ExamplesPanel :admin="false" />
        </section>
      </template>
    </main>
  </div>
</template>

<script>
import { Button as VanButton } from 'vant'
import BrandNav from '../../components/BrandNav.vue'
import { hasRole } from '../../stores/auth.js'
import api from './api.js'
import RunDetail from './components/RunDetail.vue'
import ExamplesPanel from './components/ExamplesPanel.vue'
import EvaluationPanel from './components/EvaluationPanel.vue'
import { parseSpecification, RUN_STATUS_LABELS, sampleInput, VERSION_STATUS_LABELS } from './studio.js'

const POLL_INTERVAL = 2500

export default {
  name: 'SkillStudio',
  components: { BrandNav, RunDetail, ExamplesPanel, EvaluationPanel, VanButton },
  data() {
    return {
      isAdmin: hasRole('admin'),
      versions: [],
      selectedVersion: null,
      activeAdminTab: 'skills',
      specificationText: '',
      inputText: JSON.stringify(sampleInput(), null, 2),
      runtimeInstruction: '',
      runs: [],
      selectedRun: null,
      caseId: this.$route.query.case_id ? String(this.$route.query.case_id) : '',
      caseIdDraft: this.$route.query.case_id ? String(this.$route.query.case_id) : '',
      loading: false,
      saving: false,
      publishing: false,
      running: false,
      caseLoading: false,
      message: '',
      messageKind: '',
      pollTimer: null,
      RUN_STATUS_LABELS,
      VERSION_STATUS_LABELS
    }
  },
  computed: {
    editable() {
      return this.isAdmin && this.selectedVersion?.status === 'DRAFT'
    },
    specError() {
      return this.editable ? parseSpecification(this.specificationText).error : ''
    },
    inputError() {
      if (!this.isAdmin) return ''
      try {
        const parsed = JSON.parse(this.inputText)
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? '' : '输入快照必须是 JSON 对象。'
      } catch (error) {
        return `JSON 格式错误：${error.message}`
      }
    }
  },
  mounted() {
    if (this.isAdmin) this.loadVersions()
    else if (this.caseId) this.loadCaseRuns()
  },
  beforeUnmount() {
    this.clearPoll()
  },
  methods: {
    async loadVersions() {
      this.loading = true
      try {
        this.versions = await api.getSkillVersions()
        const current = this.versions.find(item => item.id === this.selectedVersion?.id) || this.versions[0]
        if (current) this.selectVersion(current)
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '无法读取 Skill 版本。', 'error')
      } finally {
        this.loading = false
      }
    },
    selectVersion(version) {
      this.selectedVersion = version
      this.specificationText = JSON.stringify(version.specification_json, null, 2)
      this.selectedRun = null
      this.loadRuns()
    },
    async createDraft() {
      if (!this.selectedVersion) return
      this.saving = true
      try {
        const created = await api.createSkillVersion({
          skill_key: this.selectedVersion.skill_key,
          name: this.selectedVersion.name,
          category: this.selectedVersion.category,
          specification_json: this.selectedVersion.specification_json
        })
        this.versions.unshift(created)
        this.selectVersion(created)
        this.showMessage(`已创建 ${created.skill_key} v${created.version} 草稿。`)
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '创建草稿失败。', 'error')
      } finally {
        this.saving = false
      }
    },
    async saveDraft(options = {}) {
      const parsed = parseSpecification(this.specificationText)
      if (parsed.error) {
        this.showMessage(parsed.error, 'error')
        if (options.rethrow) throw new Error(parsed.error)
        return
      }
      this.saving = true
      try {
        const updated = await api.updateSkillVersion(this.selectedVersion.id, {
          name: parsed.value.identity?.name || this.selectedVersion.name,
          category: this.selectedVersion.category,
          specification_json: parsed.value
        })
        this.replaceVersion(updated)
        this.showMessage('草稿已保存。')
        return updated
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '保存草稿失败。', 'error')
        if (options.rethrow) throw error
      } finally {
        this.saving = false
      }
    },
    async publish() {
      const parsed = parseSpecification(this.specificationText)
      if (parsed.error) return
      this.publishing = true
      try {
        if (this.selectedVersion.status === 'DRAFT') await this.saveDraft({ rethrow: true })
        const published = await api.publishSkillVersion(this.selectedVersion.id)
        this.replaceVersion(published)
        this.showMessage(`已发布 ${published.skill_key} v${published.version}。`)
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '发布失败。', 'error')
      } finally {
        this.publishing = false
      }
    },
    replaceVersion(version) {
      this.versions = this.versions.map(item => item.id === version.id ? version : item)
      this.selectedVersion = version
      this.specificationText = JSON.stringify(version.specification_json, null, 2)
    },
    async startRun() {
      if (this.inputError || !this.selectedVersion) return
      this.running = true
      try {
        const run = await api.runSkill(this.selectedVersion.id, {
          idempotency_key: globalThis.crypto?.randomUUID?.() || `studio-${Date.now()}-${Math.random()}`,
          input_data: JSON.parse(this.inputText),
          runtime_instruction: this.runtimeInstruction || null
        })
        this.selectedRun = run
        await this.loadRuns()
        this.startPoll()
        this.showMessage(`Run #${run.id} 已加入队列。`)
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '运行请求失败。', 'error')
      } finally {
        this.running = false
      }
    },
    async startEvaluation(caseKeys) {
      if (!this.selectedVersion) throw new Error('请先选择 Skill 版本。')
      if (this.editable) await this.saveDraft({ rethrow: true })
      return api.startSkillEvaluation(this.selectedVersion.id, { case_keys: caseKeys })
    },
    async loadRuns() {
      if (!this.selectedVersion) return
      try {
        this.runs = await api.getSkillRuns(this.selectedVersion.id)
        if (this.selectedRun) this.selectedRun = this.runs.find(run => run.id === this.selectedRun.id) || this.selectedRun
        if (this.runs.some(run => ['PENDING', 'RUNNING'].includes(run.status))) this.startPoll()
        else this.clearPoll()
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '无法读取运行记录。', 'error')
      }
    },
    selectRun(run) {
      this.selectedRun = run
    },
    async loadCaseRuns() {
      const id = Number(this.caseIdDraft)
      if (!Number.isSafeInteger(id) || id < 1) return
      this.caseLoading = true
      try {
        this.caseId = String(id)
        this.$router.replace({ query: { ...this.$route.query, case_id: String(id) } })
        this.runs = await api.getCaseSkillRuns(id)
        this.selectedRun = this.runs[0] || null
        if (this.runs.some(run => ['PENDING', 'RUNNING'].includes(run.status))) this.startPoll()
        else this.clearPoll()
        this.message = ''
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '无权查看该 Case 或读取失败。', 'error')
        this.runs = []
        this.selectedRun = null
        this.clearPoll()
      } finally {
        this.caseLoading = false
      }
    },
    async refreshCaseRuns() {
      if (!this.caseId) return
      try {
        this.runs = await api.getCaseSkillRuns(Number(this.caseId))
        if (this.selectedRun) this.selectedRun = this.runs.find(run => run.id === this.selectedRun.id) || this.selectedRun
        else this.selectedRun = this.runs[0] || null
        if (!this.runs.some(run => ['PENDING', 'RUNNING'].includes(run.status))) this.clearPoll()
      } catch (error) {
        this.showMessage(error.response?.data?.detail || '无法读取运行记录。', 'error')
        this.clearPoll()
      }
    },
    startPoll() {
      if (this.pollTimer) return
      this.pollTimer = window.setInterval(() => {
        if (this.isAdmin) this.loadRuns()
        else this.refreshCaseRuns()
      }, POLL_INTERVAL)
    },
    clearPoll() {
      if (this.pollTimer) window.clearInterval(this.pollTimer)
      this.pollTimer = null
    },
    formatDate(value) {
      return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
    },
    showMessage(message, kind = '') {
      this.message = message
      this.messageKind = kind
    }
  }
}
</script>

<style scoped src="./studio.css"></style>
