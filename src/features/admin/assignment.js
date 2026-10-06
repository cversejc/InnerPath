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

export function consultantsForDirection(consultants, direction) {
  if (!DIRECTION_CAPABILITIES[direction]) return []
  return consultants.filter(consultant => consultant.is_active !== false && consultantCoversDirection(consultant, direction))
}

export function consultantsForSpecialty(consultants, specialty) {
  if (!['mingli', 'psychology'].includes(specialty)) return []
  return consultants.filter(consultant => consultant.is_active !== false && consultantCanHandle(consultant, specialty))
}
