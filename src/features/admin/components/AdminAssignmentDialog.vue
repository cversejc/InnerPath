<script setup>
import { computed, ref, watch } from 'vue'
import { Button as VanButton, Dialog as VanDialog } from 'vant'
import AdminIconButton from './AdminIconButton.vue'
import { consultantOptionLabel, consultantsForDirection, consultantsForSpecialty } from '../assignment.js'
import { CONSULTATION_TYPE_LABELS } from '../../../utils/displayLabels.js'

const props = defineProps({
  assignmentError: { type: String, default: '' },
  assignmentSavingKey: { type: String, default: '' },
  consultants: { type: Array, default: () => [] },
  consultantWorkloads: { type: Array, default: () => [] },
  request: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const consultationType = ref('')
const consultantId = ref('')
const mingliConsultantId = ref('')
const psychologyConsultantId = ref('')

const directionCandidates = computed(() => consultantsForDirection(props.consultants, consultationType.value, props.consultantWorkloads))
const mingliCandidates = computed(() => consultantsForSpecialty(props.consultants, 'mingli', props.consultantWorkloads))
const psychologyCandidates = computed(() => consultantsForSpecialty(props.consultants, 'psychology', props.consultantWorkloads))
const isSaving = computed(() => Boolean(props.request && props.assignmentSavingKey.startsWith(`${props.request.id}:`)))
const assignmentKey = computed(() => props.request ? `${props.request.id}:single` : '')
const singleChanged = computed(() => Boolean(props.request && (
  consultationType.value !== (props.request.consultation_type || '') ||
  consultantId.value !== idValue(props.request.assigned_consultant_id)
)))

watch(() => props.request, request => {
  consultationType.value = request?.consultation_type || ''
  consultantId.value = idValue(request?.assigned_consultant_id)
  mingliConsultantId.value = idValue(request?.assigned_mingli_consultant_id)
  psychologyConsultantId.value = idValue(request?.assigned_psychology_consultant_id)
}, { immediate: true })

function idValue(value) {
  return value === null || value === undefined ? '' : String(value)
}

function consultationTypeLabel(value) {
  return CONSULTATION_TYPE_LABELS[value] || '方向待确认'
}

function optionLabel(consultant, candidates, specialty) {
  return consultantOptionLabel(
    consultant,
    props.consultantWorkloads,
    specialty,
    String(consultant.id) === String(candidates[0]?.id)
  )
}

function suggestionText(candidates, specialty) {
  if (!candidates.length) return ''
  if (!props.consultantWorkloads.length) return '工作量暂不可用，仍可手动分配。'
  return optionLabel(candidates[0], candidates, specialty)
}

function singleOptionChanged(event) {
  consultationType.value = event.target.value
  if (consultantId.value && !directionCandidates.value.some(consultant => String(consultant.id) === consultantId.value)) {
    consultantId.value = ''
  }
}

function slotChanged(specialty) {
  const value = specialty === 'mingli' ? mingliConsultantId.value : psychologyConsultantId.value
  const current = specialty === 'mingli'
    ? props.request?.assigned_mingli_consultant_id
    : props.request?.assigned_psychology_consultant_id
  return value !== idValue(current)
}

function saveSingle() {
  if (!props.request || !consultationType.value || !singleChanged.value || isSaving.value) return
  emit('save', {
    requestId: props.request.id,
    consultantId: consultantId.value ? Number(consultantId.value) : null,
    consultationType: consultationType.value,
    mode: 'single'
  })
}

function saveSpecialty(specialty) {
  if (!props.request || !slotChanged(specialty) || isSaving.value) return
  const value = specialty === 'mingli' ? mingliConsultantId.value : psychologyConsultantId.value
  emit('save', {
    requestId: props.request.id,
    consultantId: value ? Number(value) : null,
    consultantType: specialty,
    consultationType: props.request.consultation_type || undefined,
    mode: specialty
  })
}
</script>

<template>
  <VanDialog
    :show="Boolean(request)"
    class="admin-assignment-dialog"
    :title="request ? `分配申请 #${request.id}` : '分配申请'"
    :close-on-click-overlay="false"
    :show-confirm-button="false"
    :show-cancel-button="false"
  >
    <div v-if="request" class="admin-assignment-content">
      <div class="assignment-dialog-heading">
        <div><strong>{{ request.user_name || `用户 #${request.user_id}` }}</strong><small>{{ request.user_phone || '—' }} · {{ consultationTypeLabel(request.consultation_type) }}</small></div>
        <AdminIconButton icon="close" label="关闭分配窗口" :disabled="isSaving" @click="emit('close')" />
      </div>

      <p v-if="assignmentError" class="assignment-error" role="alert">{{ assignmentError }}</p>

      <template v-if="request.is_collaborative">
        <p class="assignment-help">综合申请分为命理与心理两个席位；各席位候选按本专业当前在办数和超 24 小时未更新数排序。</p>
        <section class="assignment-slot">
          <div><h3>命理负责人</h3><small>{{ request.assigned_mingli_consultant_name || '待分配' }}</small></div>
          <label>咨询师<select v-model="mingliConsultantId" :disabled="isSaving" aria-label="选择命理负责人"><option value="">待分配</option><option v-if="mingliConsultantId && !mingliCandidates.some(consultant => String(consultant.id) === mingliConsultantId)" :value="mingliConsultantId" disabled>{{ request.assigned_mingli_consultant_name || `咨询师 #${mingliConsultantId}` }} · 当前不可分配</option><option v-for="consultant in mingliCandidates" :key="consultant.id" :value="String(consultant.id)">{{ optionLabel(consultant, mingliCandidates, 'mingli') }}</option></select><small class="assignment-suggestion">{{ suggestionText(mingliCandidates, 'mingli') }}</small></label>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!slotChanged('mingli') || isSaving" :loading="assignmentSavingKey === `${request.id}:mingli`" loading-text="保存中…" @click="saveSpecialty('mingli')">保存命理席位</VanButton>
        </section>
        <section class="assignment-slot">
          <div><h3>心理负责人</h3><small>{{ request.assigned_psychology_consultant_name || '待分配' }}</small></div>
          <label>咨询师<select v-model="psychologyConsultantId" :disabled="isSaving" aria-label="选择心理负责人"><option value="">待分配</option><option v-if="psychologyConsultantId && !psychologyCandidates.some(consultant => String(consultant.id) === psychologyConsultantId)" :value="psychologyConsultantId" disabled>{{ request.assigned_psychology_consultant_name || `咨询师 #${psychologyConsultantId}` }} · 当前不可分配</option><option v-for="consultant in psychologyCandidates" :key="consultant.id" :value="String(consultant.id)">{{ optionLabel(consultant, psychologyCandidates, 'psychology') }}</option></select><small class="assignment-suggestion">{{ suggestionText(psychologyCandidates, 'psychology') }}</small></label>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!slotChanged('psychology') || isSaving" :loading="assignmentSavingKey === `${request.id}:psychology`" loading-text="保存中…" @click="saveSpecialty('psychology')">保存心理席位</VanButton>
        </section>
      </template>

      <div v-else class="assignment-single-form">
        <label>咨询方向<select :value="consultationType" :disabled="isSaving" aria-label="选择咨询方向" @change="singleOptionChanged"><option value="">请选择方向</option><option value="metaphysics">命理</option><option value="psychology">心理</option><option value="integrated">综合（命理 + 心理）</option></select></label>
        <label>咨询师<select v-model="consultantId" :disabled="!consultationType || isSaving" aria-label="选择咨询师"><option value="">待分配</option><option v-if="consultantId && !directionCandidates.some(consultant => String(consultant.id) === consultantId)" :value="consultantId" disabled>{{ request.assigned_consultant_name || `咨询师 #${consultantId}` }} · 当前不可分配</option><option v-for="consultant in directionCandidates" :key="consultant.id" :value="String(consultant.id)">{{ optionLabel(consultant, directionCandidates, consultationType === 'metaphysics' ? 'mingli' : consultationType === 'psychology' ? 'psychology' : null) }}</option></select><small class="assignment-suggestion">{{ suggestionText(directionCandidates, consultationType === 'metaphysics' ? 'mingli' : consultationType === 'psychology' ? 'psychology' : null) }}</small></label>
        <p v-if="consultationType && !directionCandidates.length" class="assignment-help">暂无具备该方向能力的在职咨询师。</p>
        <div class="assignment-dialog-actions">
          <VanButton class="filter-reset" type="default" plain native-type="button" :disabled="isSaving" @click="emit('close')">取消</VanButton>
          <VanButton class="primary-button" type="primary" native-type="button" :disabled="!singleChanged || !consultationType || isSaving" :loading="assignmentSavingKey === assignmentKey" loading-text="保存中…" @click="saveSingle">保存分配</VanButton>
        </div>
      </div>
    </div>
  </VanDialog>
</template>
