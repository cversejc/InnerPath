<script setup>
import { computed, ref, watch } from 'vue'
import { Button as VanButton, Dialog as VanDialog } from 'vant'
import AdminIconButton from './AdminIconButton.vue'
import { consultantsForDirection, consultantsForSpecialty } from '../assignment.js'

const props = defineProps({
  assignmentError: { type: String, default: '' },
  assignmentSavingKey: { type: String, default: '' },
  consultants: { type: Array, default: () => [] },
  request: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const consultationType = ref('')
const consultantId = ref('')
const mingliConsultantId = ref('')
const psychologyConsultantId = ref('')

const directionCandidates = computed(() => consultantsForDirection(props.consultants, consultationType.value))
const mingliCandidates = computed(() => consultantsForSpecialty(props.consultants, 'mingli'))
const psychologyCandidates = computed(() => consultantsForSpecialty(props.consultants, 'psychology'))
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
        <div><strong>{{ request.user_name || `用户 #${request.user_id}` }}</strong><small>{{ request.user_phone || '—' }} · {{ request.consultation_type ? ({ metaphysics: '命理', psychology: '心理', integrated: '综合' }[request.consultation_type]) : '方向待确认' }}</small></div>
        <AdminIconButton icon="close" label="关闭分配窗口" :disabled="isSaving" @click="emit('close')" />
      </div>

      <p v-if="assignmentError" class="assignment-error" role="alert">{{ assignmentError }}</p>

      <template v-if="request.is_collaborative">
        <p class="assignment-help">综合申请分为命理与心理两个席位，可分别指定负责人。</p>
        <section class="assignment-slot">
          <div><h3>命理负责人</h3><small>{{ request.assigned_mingli_consultant_name || '待分配' }}</small></div>
          <label>咨询师<select v-model="mingliConsultantId" :disabled="isSaving" aria-label="选择命理负责人"><option value="">待分配</option><option v-if="mingliConsultantId && !mingliCandidates.some(consultant => String(consultant.id) === mingliConsultantId)" :value="mingliConsultantId" disabled>{{ request.assigned_mingli_consultant_name || `咨询师 #${mingliConsultantId}` }} · 当前不可分配</option><option v-for="consultant in mingliCandidates" :key="consultant.id" :value="String(consultant.id)">{{ consultant.name }} · #{{ consultant.id }}</option></select></label>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!slotChanged('mingli') || isSaving" :loading="assignmentSavingKey === `${request.id}:mingli`" loading-text="保存中…" @click="saveSpecialty('mingli')">保存命理席位</VanButton>
        </section>
        <section class="assignment-slot">
          <div><h3>心理负责人</h3><small>{{ request.assigned_psychology_consultant_name || '待分配' }}</small></div>
          <label>咨询师<select v-model="psychologyConsultantId" :disabled="isSaving" aria-label="选择心理负责人"><option value="">待分配</option><option v-if="psychologyConsultantId && !psychologyCandidates.some(consultant => String(consultant.id) === psychologyConsultantId)" :value="psychologyConsultantId" disabled>{{ request.assigned_psychology_consultant_name || `咨询师 #${psychologyConsultantId}` }} · 当前不可分配</option><option v-for="consultant in psychologyCandidates" :key="consultant.id" :value="String(consultant.id)">{{ consultant.name }} · #{{ consultant.id }}</option></select></label>
          <VanButton class="secondary-button compact-button" type="default" plain native-type="button" :disabled="!slotChanged('psychology') || isSaving" :loading="assignmentSavingKey === `${request.id}:psychology`" loading-text="保存中…" @click="saveSpecialty('psychology')">保存心理席位</VanButton>
        </section>
      </template>

      <div v-else class="assignment-single-form">
        <label>咨询方向<select :value="consultationType" :disabled="isSaving" aria-label="选择咨询方向" @change="singleOptionChanged"><option value="">请选择方向</option><option value="metaphysics">命理</option><option value="psychology">心理</option><option value="integrated">综合（命理 + 心理）</option></select></label>
        <label>咨询师<select v-model="consultantId" :disabled="!consultationType || isSaving" aria-label="选择咨询师"><option value="">待分配</option><option v-if="consultantId && !directionCandidates.some(consultant => String(consultant.id) === consultantId)" :value="consultantId" disabled>{{ request.assigned_consultant_name || `咨询师 #${consultantId}` }} · 当前不可分配</option><option v-for="consultant in directionCandidates" :key="consultant.id" :value="String(consultant.id)">{{ consultant.name }} · #{{ consultant.id }}</option></select></label>
        <p v-if="consultationType && !directionCandidates.length" class="assignment-help">暂无具备该方向能力的在职咨询师。</p>
        <div class="assignment-dialog-actions">
          <VanButton class="filter-reset" type="default" plain native-type="button" :disabled="isSaving" @click="emit('close')">取消</VanButton>
          <VanButton class="primary-button" type="primary" native-type="button" :disabled="!singleChanged || !consultationType || isSaving" :loading="assignmentSavingKey === assignmentKey" loading-text="保存中…" @click="saveSingle">保存分配</VanButton>
        </div>
      </div>
    </div>
  </VanDialog>
</template>
