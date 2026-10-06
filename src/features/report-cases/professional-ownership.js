export const specialtyLabels = {
  mingli: '命理咨询师',
  psychology: '心理咨询师',
  integrated: '综合咨询师'
}
export const specialtyFields = { mingli: 'assigned_mingli_consultant_id', psychology: 'assigned_psychology_consultant_id' }

export function consultantCanHandle(consultant, capability) {
  if (!consultant || !specialtyFields[capability]) return false
  if (consultant.consultant_type === capability || consultant.consultant_type === 'integrated') return true
  const specialties = consultant.consultant_specialties || []
  return capability === 'mingli'
    ? specialties.includes('metaphysics') || specialties.includes('mingli')
    : specialties.includes('psychology')
}

export function ownsRequest(request, actor) {
  return actor?.role === 'admin' || [request?.assigned_consultant_id,
    request?.assigned_mingli_consultant_id, request?.assigned_psychology_consultant_id]
    .some(id => id != null && id === actor?.id)
}

export function canAcceptRequest(request, actor) {
  if (!request || ['delivered', 'withdrawn', 'rejected'].includes(request.status)) return false
  if (actor?.role !== 'consultant') return false
  const capabilities = Object.keys(specialtyFields).filter(capability => consultantCanHandle(actor, capability))
  if (request.consultation_type === 'metaphysics') capabilities.splice(1)
  if (request.consultation_type === 'psychology') capabilities.splice(0, 1)
  if (capabilities.length) return capabilities.some(capability => request[specialtyFields[capability]] == null)
  return request.status === 'submitted' && !request.assigned_consultant_id
}

export function canHandleStep(step, actor) {
  if (!step || !actor) return false
  if (actor.role === 'admin') return true
  if (actor.role !== 'consultant') return false
  if (specialtyFields[step.required_capability]) {
    return consultantCanHandle(actor, step.required_capability) && step.assignee_id === actor.id
  }
  return (!step.required_capability || step.required_capability === 'consultant') &&
    (step.assignee_id == null || step.assignee_id === actor.id)
}
