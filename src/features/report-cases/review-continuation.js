import { reportFragmentOrder, reportFragmentTitle } from './stages.js'

export function orderedReportFragments(content, contentPlan) {
  const positions = new Map((contentPlan?.fragments || []).map((item, index) => [item.fragment_key, index]))
  return (content.fragments || []).filter(item => item.fragment_type === 'REPORT')
    .sort((a, b) => (positions.get(a.fragment_key) ?? reportFragmentOrder(a.fragment_key))
      - (positions.get(b.fragment_key) ?? reportFragmentOrder(b.fragment_key)))
}

export function nextPendingRecord(items, currentKey, field, pending) {
  const index = items.findIndex(item => String(item[field]) === String(currentKey))
  const after = items.slice(index + 1).find(pending)
  const before = items.slice(0, Math.max(0, index)).find(pending)
  return after || before || null
}

export function reportFragmentReviewDraft(fragment) {
  return {
    expected_revision_no: fragment.revision_no,
    fragment_type: fragment.fragment_type,
    title: reportFragmentTitle(fragment.fragment_key, fragment.title), content: fragment.content,
    edit_kind: 'STYLE', status: fragment.status === 'STALE' ? 'PROPOSED' : fragment.status,
    finding_refs: (fragment.source_snapshot?.findings || []).map(item => item.finding_key),
    fragment_refs: (fragment.source_snapshot?.fragments || []).map(item => item.fragment_key),
    evidence_refs: (fragment.source_snapshot?.evidence || []).map(item => item.evidence_key)
  }
}

export function orderedQualityIssues(issues) {
  const priority = { BLOCK: 0, MAJOR: 1, MINOR: 2 }
  return [...issues].sort((a, b) => Number(a.status !== 'OPEN') - Number(b.status !== 'OPEN')
    || (priority[a.severity] ?? 3) - (priority[b.severity] ?? 3) || a.id - b.id)
}
