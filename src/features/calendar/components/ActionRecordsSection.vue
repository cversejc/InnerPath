<script setup>
import { computed } from 'vue'

const props = defineProps({
  recordDraft: { type: Object, required: true },
  recordError: { type: String, default: '' },
  recordFeedback: { type: String, default: '' },
  recordSource: { type: String, default: 'local' },
  savingRecord: { type: Boolean, default: false },
  selectedDate: { type: String, default: '' },
  selectedEntry: { type: Object, required: true },
  selectedRecords: { type: Array, default: () => [] },
  showRecordForm: { type: Boolean, default: false },
  todayDate: { type: String, default: '' }
})

const emit = defineEmits([
  'close-record-form',
  'open-record-form',
  'quick-record',
  'remove-record',
  'save-record',
  'update-record-draft'
])

const recordedSuggestions = computed(() => new Set(
  props.selectedRecords
    .filter(record => record.kind === 'action' && record.status !== 'skipped')
    .map(record => record.content)
))

function isQuickRecordSaved(item) {
  return recordedSuggestions.value.has(item)
}

function statusText(status) {
  return { done: '已完成', doing: '进行中', skipped: '已跳过' }[status] || '已记录'
}

function updateDraft(field, value) {
  emit('update-record-draft', { [field]: value })
}
</script>

<template>
  <section class="actual-records" aria-labelledby="actual-record-title">
    <div class="actual-records-head">
      <div>
        <span class="detail-section-kicker">KEEP A TRACE</span>
        <h4 id="actual-record-title">{{ selectedDate === todayDate ? '今天实际做了什么' : '这天实际做了什么' }}</h4>
      </div>
      <span class="actual-count">{{ selectedRecords.length }} 条</span>
    </div>
    <p class="actual-records-intro">把建议和真实发生的事并排保存，日后才能看见自己的节奏。</p>

    <div v-if="selectedRecords.length" class="actual-record-list">
      <article v-for="record in selectedRecords" :key="record.id" class="actual-record-item">
        <div class="actual-record-meta">
          <span class="record-kind" :class="`kind-${record.kind}`">{{ record.kind === 'decision' ? '决策' : '行动' }}</span>
          <span class="record-status" :class="`status-${record.status}`">{{ statusText(record.status) }}</span>
          <button class="record-delete" type="button" @click.stop="emit('remove-record', record)">删除</button>
        </div>
        <p>{{ record.content }}</p>
        <small v-if="record.note">{{ record.note }}</small>
      </article>
    </div>
    <p v-else class="actual-record-empty">还没有记录。可以从下面的建议开始，也可以写下一件今天真实发生的事。</p>

    <div v-if="selectedEntry.suitable?.length" class="quick-records">
      <div class="quick-records-head"><span>从今日建议记一笔</span><small>已经做过的可以直接加入</small></div>
      <button
        v-for="item in selectedEntry.suitable"
        :key="item"
        type="button"
        class="quick-record-button"
        :class="{ recorded: isQuickRecordSaved(item) }"
        :disabled="isQuickRecordSaved(item) || savingRecord"
        @click="emit('quick-record', item)"
      >
        <span>{{ item }}</span><b>{{ isQuickRecordSaved(item) ? '已记录' : '＋ 已做' }}</b>
      </button>
    </div>

    <button v-if="!showRecordForm" class="record-add-button" type="button" @click="emit('open-record-form')">
      <span>＋</span> 记录一件事 / 一个决定
    </button>

    <form v-else class="record-form" :aria-describedby="recordError ? 'record-error' : undefined" @submit.prevent="emit('save-record')">
      <div class="record-form-head">
        <span>新记录</span>
        <button type="button" @click="emit('close-record-form')">收起</button>
      </div>
      <div class="record-form-grid">
        <label><span>记录类型</span><select :value="recordDraft.kind" @change="updateDraft('kind', $event.target.value)"><option value="action">行动</option><option value="decision">决策</option></select></label>
        <label><span>当前状态</span><select :value="recordDraft.status" @change="updateDraft('status', $event.target.value)"><option value="done">已完成</option><option value="doing">进行中</option><option value="skipped">跳过</option></select></label>
      </div>
      <label class="record-form-field"><span>实际发生了什么</span><textarea :value="recordDraft.content" rows="3" maxlength="240" placeholder="例如：完成了今天最重要的一件事" @input="updateDraft('content', $event.target.value)"></textarea></label>
      <label class="record-form-field"><span>结果 / 备注（可选）</span><input :value="recordDraft.note" maxlength="240" placeholder="例如：比预想顺利，明天继续细化" @input="updateDraft('note', $event.target.value)"></label>
      <div class="record-form-actions">
        <button class="secondary-button" type="button" @click="emit('close-record-form')">取消</button>
        <button class="primary-button" type="submit" :disabled="savingRecord" :aria-busy="savingRecord">{{ savingRecord ? '保存中…' : '保存记录' }}</button>
      </div>
      <p v-if="recordError" id="record-error" class="record-error" role="alert" aria-live="assertive">{{ recordError }}</p>
    </form>
    <p v-if="recordFeedback" class="record-feedback" role="status" aria-live="polite">{{ recordFeedback }}</p>
    <p class="record-storage-note"><i></i>{{ recordSource === 'api' ? '已同步到你的账号' : '当前暂存于本设备' }}</p>
  </section>
</template>
