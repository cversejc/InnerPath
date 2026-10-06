<template>
  <fieldset class="evidence-reference-picker" :disabled="disabled">
    <legend>{{ label }} · 已关联 {{ selectedKeys.length }} 项</legend>
    <p v-if="selectedItems.length" class="evidence-reference-heading">当前依据</p>
    <label v-for="item in selectedItems" :key="item.evidence_key" class="evidence-reference-row">
      <input type="checkbox" checked @change="toggle(item.evidence_key, false)" />
      <span class="evidence-reference-copy">
        <strong>{{ evidenceTitle(item) }}</strong>
        <small>{{ evidenceSummary(item) }}</small>
        <small v-if="item.status !== 'ACTIVE'" class="evidence-reference-stale">资料已更新或撤回，移除后才能确认。</small>
      </span>
    </label>
    <p v-if="!selectedKeys.length" class="evidence-reference-empty">尚未关联资料。可从当前节点相关资料中添加；其他资料可搜索。</p>
    <details class="evidence-reference-search">
      <summary>添加其他资料依据 · {{ activeItems.length }} 项可选</summary>
      <label class="evidence-reference-query">
        搜索全案资料
        <input v-model.trim="query" type="search" autocomplete="off" placeholder="输入资料名称或内容" />
      </label>
      <template v-if="preferredItems.length">
        <p class="evidence-reference-heading">当前节点相关资料</p>
        <label v-for="item in preferredItems" :key="item.evidence_key" class="evidence-reference-row">
          <input type="checkbox" :checked="selectedKeys.includes(item.evidence_key)" @change="toggle(item.evidence_key, $event.target.checked)" />
          <span class="evidence-reference-copy"><strong>{{ evidenceTitle(item) }}</strong><small>{{ evidenceSummary(item) }}</small></span>
        </label>
      </template>
      <template v-if="query">
        <p class="evidence-reference-heading">其他匹配资料</p>
        <label v-for="item in otherMatchingItems" :key="item.evidence_key" class="evidence-reference-row">
          <input type="checkbox" :checked="selectedKeys.includes(item.evidence_key)" @change="toggle(item.evidence_key, $event.target.checked)" />
          <span class="evidence-reference-copy"><strong>{{ evidenceTitle(item) }}</strong><small>{{ evidenceSummary(item) }}</small></span>
        </label>
        <p v-if="!otherMatchingItems.length" class="evidence-reference-empty">没有其他匹配资料。</p>
      </template>
      <p v-else class="evidence-reference-empty">输入关键词可搜索并添加其他资料。</p>
    </details>
  </fieldset>
</template>

<script>
import { formatConsultantEvidenceValue, isVisibleConsultantEvidence, reportEvidenceTitle, visibleConsultantEvidence } from '../workbench-inputs.js'

function references(value) {
  const values = Array.isArray(value) ? value : String(value || '').split(/[\n,，]/)
  return [...new Set(values.map(item => String(item || '').trim()).filter(Boolean))]
}

export default {
  name: 'EvidenceReferencePicker',
  props: {
    modelValue: { type: [Array, String], default: () => [] },
    items: { type: Array, default: () => [] },
    preferredKeys: { type: Array, default: () => [] },
    label: { type: String, default: '资料依据' },
    disabled: Boolean
  },
  emits: ['update:modelValue'],
  data: () => ({ query: '' }),
  computed: {
    selectedKeys() { return references(this.modelValue) },
    displayItems() {
      const items = new Map(visibleConsultantEvidence(this.items).map(item => [item.evidence_key, item]))
      const relevantKeys = new Set([...this.selectedKeys, ...this.preferredKeys])
      for (const item of this.items) {
        if (relevantKeys.has(item.evidence_key) && isVisibleConsultantEvidence(item) && !items.has(item.evidence_key)) {
          items.set(item.evidence_key, item)
        }
      }
      return [...items.values()]
    },
    itemsByKey() { return new Map(this.displayItems.map(item => [item.evidence_key, item])) },
    selectedItems() {
      return this.selectedKeys.map(key => this.itemsByKey.get(key) || { evidence_key: key, status: 'MISSING' })
    },
    activeItems() { return this.displayItems.filter(item => item.status === 'ACTIVE') },
    preferredKeySet() { return new Set(this.preferredKeys) },
    preferredItems() {
      const query = this.query.toLocaleLowerCase()
      return this.activeItems
        .filter(item => this.preferredKeySet.has(item.evidence_key) && !this.selectedKeys.includes(item.evidence_key))
        .filter(item => !query || this.searchText(item).includes(query))
    },
    otherMatchingItems() {
      if (!this.query) return []
      const query = this.query.toLocaleLowerCase()
      return this.activeItems
        .filter(item => !this.preferredKeySet.has(item.evidence_key) && !this.selectedKeys.includes(item.evidence_key))
        .filter(item => this.searchText(item).includes(query))
    }
  },
  methods: {
    evidenceTitle(item) { return item.status === 'MISSING' ? '资料已更新或无法找到' : reportEvidenceTitle(item) },
    evidenceSummary(item) {
      if (item.status === 'MISSING') return item.evidence_key
      const value = formatConsultantEvidenceValue(item.value_json, item.source_type)
      const summary = String(value || '').replace(/\s+/g, ' ').trim()
      return summary.length > 220 ? `${summary.slice(0, 220)}…` : summary || '没有可显示的资料摘要。'
    },
    searchText(item) { return `${this.evidenceTitle(item)} ${this.evidenceSummary(item)} ${item.evidence_key}`.toLocaleLowerCase() },
    toggle(key, checked) {
      const next = this.selectedKeys.filter(item => item !== key)
      if (checked) next.push(key)
      const unique = [...new Set(next)]
      this.$emit('update:modelValue', Array.isArray(this.modelValue) ? unique : unique.join('\n'))
    }
  }
}
</script>

<style scoped>
.evidence-reference-picker { display: grid; gap: var(--space-2); min-width: 0; margin: 0; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--button-radius); }
.evidence-reference-picker legend { padding: 0 var(--space-1); color: var(--ink-soft); font-size: var(--text-body-sm); font-weight: var(--weight-semibold); }
.evidence-reference-heading, .evidence-reference-empty { margin: 0; color: var(--muted); font-size: var(--text-body-sm); line-height: var(--leading-body); }
.evidence-reference-row { display: flex; align-items: flex-start; gap: var(--space-2); min-width: 0; min-height: var(--touch-target); padding: var(--space-2) 0; color: var(--ink); }
.evidence-reference-row > input { flex: 0 0 auto; width: 18px; height: 18px; margin-top: 3px; accent-color: var(--jade); }
.evidence-reference-copy { display: grid; gap: var(--space-1); min-width: 0; }
.evidence-reference-copy strong { font-size: var(--text-body); font-weight: var(--weight-medium); overflow-wrap: anywhere; }
.evidence-reference-copy small { color: var(--ink-soft); font-size: var(--text-caption); line-height: var(--leading-body); overflow-wrap: anywhere; }
.evidence-reference-copy .evidence-reference-stale { color: var(--cinnabar-deep); }
.evidence-reference-search { border-top: 1px solid var(--line); }
.evidence-reference-search summary { min-height: var(--touch-target); padding: var(--space-3) 0; color: var(--gold-deep); font-size: var(--text-body-sm); cursor: pointer; }
.evidence-reference-query { display: grid; gap: var(--space-2); color: var(--ink-soft); font-size: var(--text-body-sm); }
.evidence-reference-query input { width: 100%; min-width: 0; min-height: var(--touch-target); padding: var(--space-3); border: 1px solid var(--line-strong); border-radius: var(--button-radius); background: var(--paper-soft); color: var(--ink); font: inherit; font-size: var(--text-body); }
@media (max-width: 640px) { .evidence-reference-picker { padding: var(--space-2); } }
</style>
