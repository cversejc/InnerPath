import { consultantCanHandle } from '../report-cases/professional-ownership.js'

const DIRECTION_CAPABILITIES = {
  metaphysics: ['mingli'],
  psychology: ['psychology'],
  integrated: ['mingli', 'psychology']
}

export function consultantCoversDirection(consultant, direction) {
  const capabilities = DIRECTION_CAPABILITIES[direction]
  return Boolean(capabilities?.every(capability => consultantCanHandle(consultant, capability)))
}

function overallLoad(workload) {
  return {
    active_requests: Number(workload.active_requests || 0),
    stale_active_requests: Number(workload.stale_active_requests || 0)
  }
}

function workloadFor(consultant, workloads, specialty) {
  const workload = (workloads || []).find(item => Number(item.consultant_id) === Number(consultant.id))
  if (!workload) return null
  if (!specialty || !Array.isArray(workload.specialty_load)) return overallLoad(workload)

  const specialtyLoad = workload.specialty_load.find(item => item.specialty === specialty)
  return specialtyLoad
    ? overallLoad(specialtyLoad)
    : { active_requests: 0, stale_active_requests: 0 }
}

function compareConsultants(first, second) {
  return String(first.name || '').localeCompare(String(second.name || ''), 'zh-CN') ||
    Number(first.id) - Number(second.id)
}

function sortCandidatesByLoad(candidates, workloads, specialty) {
  return [...candidates].sort((first, second) => {
    const firstLoad = workloadFor(first, workloads, specialty)
    const secondLoad = workloadFor(second, workloads, specialty)
    if (!firstLoad && !secondLoad) return compareConsultants(first, second)
    if (!firstLoad) return 1
    if (!secondLoad) return -1
    return firstLoad.active_requests - secondLoad.active_requests ||
      firstLoad.stale_active_requests - secondLoad.stale_active_requests ||
      compareConsultants(first, second)
  })
}

export function consultantOptionLabel(consultant, workloads, specialty, recommended = false) {
  const name = `${consultant.name || '咨询师'} · #${consultant.id}`
  const load = workloadFor(consultant, workloads, specialty)
  if (!load) return `${name} · 工作量未加载`
  const recommendation = recommended ? ' · 建议优先' : ''
  return `${name} · 在办 ${load.active_requests} · 超 24 小时未更新 ${load.stale_active_requests}${recommendation}`
}

export function consultantsForDirection(consultants, direction, workloads = []) {
  if (!DIRECTION_CAPABILITIES[direction]) return []
  const eligible = consultants.filter(consultant => consultant.is_active !== false && consultantCoversDirection(consultant, direction))
  const specialty = direction === 'metaphysics' ? 'mingli' : direction === 'psychology' ? 'psychology' : null
  return sortCandidatesByLoad(eligible, workloads, specialty)
}

export function consultantsForSpecialty(consultants, specialty, workloads = []) {
  if (!['mingli', 'psychology'].includes(specialty)) return []
  const eligible = consultants.filter(consultant => consultant.is_active !== false && consultantCanHandle(consultant, specialty))
  return sortCandidatesByLoad(eligible, workloads, specialty)
}
