<template>
  <section class="foundation-calculation-panel" aria-label="程序计算与人工核对">
    <header class="calculation-panel-heading">
      <div>
        <p class="eyebrow">程序计算阶段</p>
        <h3>程序计算与人工核对</h3>
      </div>
      <span v-if="evidence" class="calculation-version">
        {{ evidence.source_type === 'CONSULTANT_CORRECTED' ? '已采用人工修订' : '系统测算' }}
      </span>
    </header>
    <p class="calculation-guidance">
      对照出生资料核对四柱、大运和紫微结构。程序结果是命理结构资料；发现排盘错误时，可在原展示位置直接修订。保存后，AI 分析及后续节点会改用新版本。
    </p>

    <div v-if="!evidence" class="calculation-empty">
      <p>当前还没有保存本案例的程序测算结果。运行后可以先检查结果，再开始 AI 分析。</p>
      <p v-if="errorMessage" class="calculation-validation-error" role="alert">{{ errorMessage }}</p>
      <VanButton class="primary-button" type="primary" native-type="button" :loading="saving" :disabled="readOnly || saving" @click="$emit('calculate')">
        运行程序测算
      </VanButton>
      <p v-if="readOnly" class="calculation-readonly">当前节点只读，不能运行测算。</p>
    </div>

    <template v-else>
      <p class="calculation-provenance">
        {{ evidence.source_type === 'CONSULTANT_CORRECTED' ? `人工修订版本 ${evidence.value_json?._consultant_correction?.revision || ''}` : '系统生成的测算版本' }}
        <template v-if="evidence.created_at"> · {{ evidence.created_at }}</template>
      </p>
      <p v-if="evidence.value_json?._consultant_correction?.reason && !editing" class="calculation-correction-reason">
        最近修订原因：{{ evidence.value_json._consultant_correction.reason }}
      </p>

      <FoundationEvidence
        :value="editing ? draftValue : evidence.value_json"
        :editable="editing"
        :disabled="saving"
        @update:value="updateDraft"
      />

      <div v-if="readOnly" class="calculation-readonly">当前节点只读；历史分析保留当时使用的依据。</div>
      <template v-else-if="!editing">
        <p class="calculation-audit-note">保存修订后，旧测算仍保留为历史记录；引用旧版本的判断和内容会标为需要复核。</p>
        <VanButton class="secondary-button" plain native-type="button" :disabled="saving" @click="beginEdit">
          修订程序测算
        </VanButton>
      </template>
    </template>

    <form v-if="editing" class="calculation-editor" @submit.prevent="saveCorrection">
      <label>
        修订原因
        <textarea v-model.trim="reason" rows="3" maxlength="1000" :disabled="saving" placeholder="例如：按用户确认的出生地和真太阳时重新核对后，发现时柱应为……"></textarea>
      </label>
      <p v-if="validationError" class="calculation-validation-error" role="alert">{{ validationError }}</p>
      <p v-if="errorMessage" class="calculation-validation-error" role="alert">{{ errorMessage }}</p>
      <div class="calculation-editor-actions">
        <VanButton class="secondary-button" plain native-type="button" :disabled="saving" @click="cancelEdit">取消修订</VanButton>
        <VanButton class="primary-button" type="primary" native-type="submit" :loading="saving" :disabled="saving">
          保存人工修订并更新下游依据
        </VanButton>
      </div>
    </form>
  </section>
</template>

<script>
import { Button as VanButton } from 'vant'
import FoundationEvidence from './FoundationEvidence.vue'

export default {
  name: 'FoundationCalculationPanel',
  components: { VanButton, FoundationEvidence },
  props: {
    evidence: { type: Object, default: null },
    readOnly: Boolean,
    saving: Boolean,
    errorMessage: { type: String, default: '' }
  },
  emits: ['calculate', 'save-correction'],
  data: () => ({ editing: false, draftValue: null, reason: '', validationError: '' }),
  watch: {
    evidence(value, previous) {
      if (value?.id !== previous?.id && this.editing) this.cancelEdit()
    }
  },
  methods: {
    beginEdit() {
      this.draftValue = JSON.parse(JSON.stringify(this.evidence?.value_json || {}))
      this.reason = ''
      this.validationError = ''
      this.editing = true
    },
    updateDraft(value) {
      this.draftValue = value
    },
    cancelEdit() {
      this.editing = false
      this.draftValue = null
      this.validationError = ''
    },
    saveCorrection() {
      this.validationError = ''
      const value = this.draftValue
      if (!value || typeof value !== 'object' || Array.isArray(value) || !value.bazi || typeof value.bazi !== 'object') {
        this.validationError = '测算结构不完整，请确认四柱内容仍在命盘中。'
        return
      }
      for (const key of ['year', 'month', 'day']) {
        if (!value.bazi[key]?.stem || !value.bazi[key]?.branch) {
          this.validationError = '年柱、月柱和日柱都需要填写天干与地支。'
          return
        }
      }
      if (value.bazi.hour && (!value.bazi.hour.stem || !value.bazi.hour.branch)) {
        this.validationError = '时柱已开始修订，请补全天干和地支；若不需要这项修改，请取消本次修订。'
        return
      }
      const facts = value.bazi_facts || {}
      const hasIncompleteHiddenStem = Object.values(facts.pillars || {}).some((pillar) =>
        (pillar.hidden_stems || []).some((item) => !item.stem || !item.element || !item.ten_god)
      )
      if (hasIncompleteHiddenStem) {
        this.validationError = '藏干项目需要选择天干、五行和十神；不需要的项目请移除。'
        return
      }
      if ((facts.interactions || []).some((item) => !item.type || !item.symbols || !item.pillars?.length)) {
        this.validationError = '干支关系需要填写关系类型、涉及干支和至少一个柱位。'
        return
      }
      const hasIncompleteDayun = (facts.dayun || []).some((item) =>
        !item.pillar || !item.ten_god || !item.stem_element || !item.branch_element
        || item.start_year === null || item.start_year === undefined || item.start_year === ''
        || item.end_year === null || item.end_year === undefined || item.end_year === ''
        || item.start_age === null || item.start_age === undefined || item.start_age === ''
        || item.end_age === null || item.end_age === undefined || item.end_age === ''
      )
      if (hasIncompleteDayun) {
        this.validationError = '大运阶段需要填写干支、起止年份和起止年龄；不需要的阶段请移除。'
        return
      }
      if ((facts.dayun || []).some((item) =>
        !Number.isFinite(Number(item.start_year)) || !Number.isFinite(Number(item.end_year))
        || !Number.isFinite(Number(item.start_age)) || !Number.isFinite(Number(item.end_age))
        || Number(item.end_year) < Number(item.start_year) || Number(item.end_age) < Number(item.start_age)
      )) {
        this.validationError = '大运阶段的年份和年龄应为有效数字，结束值不能早于开始值。'
        return
      }
      if (value.calculation_version !== 'mingli-v2') {
        this.validationError = '测算版本标识缺失，请联系管理员检查这份测算数据。'
        return
      }
      if (this.reason.trim().length < 3) {
        this.validationError = '请填写至少 3 个字的修订原因。'
        return
      }
      this.$emit('save-correction', { value, reason: this.reason.trim() })
    }
  }
}
</script>

<style scoped>
.foundation-calculation-panel {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--surface);
}
.calculation-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.calculation-panel-heading h3 {
  margin: 0;
  font-size: var(--text-h4);
  font-weight: var(--weight-semibold);
}
.calculation-panel-heading .eyebrow {
  margin: 0 0 var(--space-1);
  color: var(--gold-deep);
  font-size: var(--text-caption);
}
.calculation-version {
  color: var(--jade-deep);
  font-size: var(--text-body-sm);
  white-space: nowrap;
}
.calculation-guidance,
.calculation-provenance,
.calculation-correction-reason,
.calculation-audit-note,
.calculation-empty p,
.calculation-readonly {
  margin: 0;
  color: var(--ink-soft);
  font-size: var(--text-body-sm);
  line-height: var(--leading-body);
}
.calculation-provenance,
.calculation-readonly { color: var(--muted); }
.calculation-correction-reason {
  padding: var(--space-3);
  border-left: 2px solid var(--jade);
  background: var(--paper-soft);
}
.calculation-empty {
  display: grid;
  justify-items: start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px dashed var(--line-strong);
  border-radius: var(--button-radius);
  background: var(--paper-soft);
}
.calculation-editor {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border-top: 1px solid var(--line);
  background: var(--paper-soft);
}
.calculation-editor label {
  display: grid;
  gap: var(--space-2);
  color: var(--ink);
  font-size: var(--text-body);
}
.calculation-editor textarea {
  width: 100%;
  min-width: 0;
  min-height: var(--touch-target);
  padding: var(--space-3);
  border: 1px solid var(--line-strong);
  border-radius: var(--button-radius);
  background: var(--surface);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  line-height: var(--leading-body);
  resize: vertical;
}
.calculation-validation-error { margin: 0; color: var(--cinnabar-deep); font-size: var(--text-body-sm); }
.calculation-editor-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--space-2); }
.calculation-editor-actions :deep(button) { min-height: var(--touch-target); }
@media (max-width: 600px) {
  .foundation-calculation-panel { padding: var(--space-4); }
  .calculation-panel-heading { align-items: flex-start; flex-direction: column; }
  .calculation-editor-actions { align-items: stretch; flex-direction: column-reverse; }
  .calculation-editor-actions :deep(button) { width: 100%; white-space: normal; }
}
</style>
