import { reportFragmentTitle } from './stages.js'

export const cloneReviewValue = value => JSON.parse(JSON.stringify(value))

function reviewTitle(value) {
  return String(value || '').replace(/^\s*(?:\*\*)?\d+(?:\.\d+)+(?:\s*[–—-]\s*\d+(?:\.\d+)*)?\s*[、.．:：|｜-]?\s*(?:\*\*)?\s*/u, '').trim()
}

export function findingReviewTitle(finding) {
  const title = finding?.short_title || finding?.structured_data?.short_title || finding?.structured_data_json?.short_title
  const claim = reviewTitle(title || finding?.claim || '待补充的关联判断')
  return claim.split(/[，,。；;：:！？!?]/).find(part => part.trim().length >= 4)?.slice(0, 28) || claim.slice(0, 28)
}

function dependencies(finding) {
  const data = finding?.structured_data_json || finding?.structured_data || {}
  return [...new Set([
    ...(finding?.relation_refs || []).map(ref => typeof ref === 'string' ? ref : ref.finding_key),
    ...(data.block_refs || []), ...(data.reasoning_path?.resource_refs || []),
    ...(data.reasoning_path?.block_refs || [])
  ].filter(Boolean))]
}

// Directions follow the stored topic order; associations only use explicit references.
export function buildAnalysisDirections(run, content, stepId) {
  const output = run?.output_parsed || {}
  const candidates = new Map((output.findings || []).map(item => [item.finding_key, item]))
  const findings = new Map((content.findings || []).map(item => [item.finding_key, item]))
  const topics = run?.input_snapshot?.analysis_context?.sop_contract?.topics || []
  const order = new Map(topics.map((item, index) => [item.fragment_key, index]))
  const used = new Set()
  const entries = keys => {
    const visited = new Set()
    const rows = []
    function visit(key) {
      if (visited.has(key)) return
      visited.add(key)
      used.add(key)
      const candidate = candidates.get(key)
      const current = findings.get(key)
      const foreign = Boolean(current?.owner_step_task_id && current.owner_step_task_id !== stepId)
      const record = current && (foreign || !candidate || current.source_skill_run_id === run.id) ? current : candidate
      // Confirmed dependencies from previous steps already have audited lineage.
      if (!foreign) dependencies(record).forEach(visit)
      const status = record === current ? current?.status || 'PROPOSED' : 'PROPOSED'
      rows.push({ key, candidate, current, record, foreign, status,
        title: findingReviewTitle(record), editable: Boolean((candidate || current) && !foreign),
        done: Boolean(record && ['CONFIRMED', 'REJECTED'].includes(status)) })
    }
    keys.forEach(visit)
    return rows
  }
  const directions = [...(output.analysis_fragments || [])]
    .sort((a, b) => (order.get(a.fragment_key) ?? 999) - (order.get(b.fragment_key) ?? 999))
    .map(fragment => {
      const current = (content.fragments || []).find(item => item.fragment_key === fragment.fragment_key)
      const sameRun = current?.source_skill_run_id === run.id
      const record = sameRun ? current : fragment
      const refs = sameRun ? (current.source_snapshot?.findings || []).map(item => item.finding_key) : fragment.finding_refs || []
      const title = reviewTitle(record.title)
      return { key: fragment.fragment_key, title: reportFragmentTitle(fragment.fragment_key, title),
        fragment, current, record, findings: entries(refs),
        complete: Boolean(sameRun && current.status === 'CONFIRMED') }
    })
  const remaining = [...candidates.keys()].filter(key => !used.has(key))
  if (remaining.length) {
    const rows = entries(remaining)
    directions.push({ key: 'unlinked-findings', title: '其他待审判断', findings: rows,
      complete: rows.every(item => item.done) })
  }
  return directions
}

export function createFindingReview(entry) {
  const item = entry.record
  return cloneReviewValue({ expected_revision_no: entry.current?.revision_no ?? null,
    claim: item.claim, kind: item.kind, semantic_role: item.semantic_role,
    confidence: item.confidence, importance: item.importance, reportability: item.reportability,
    evidence_refs: item.evidence_refs || [], relation_refs: item.relation_refs || [],
    structured_data: item.structured_data_json || item.structured_data || {} })
}

export function createFragmentReview(direction, runId) {
  const current = direction.current?.source_skill_run_id === runId ? direction.current : null
  const snapshot = current?.source_snapshot || {}
  const source = current || direction.fragment
  return cloneReviewValue({ expected_revision_no: direction.current?.revision_no ?? null,
    title: direction.title, content: source.content,
    finding_refs: current ? (snapshot.findings || []).map(item => item.finding_key) : source.finding_refs || [],
    evidence_refs: current ? (snapshot.evidence || []).map(item => item.evidence_key) : source.evidence_refs || [],
    framework_coverage: snapshot.framework_coverage || source.framework_coverage || null,
    structured_analysis: snapshot.structured_analysis || source.structured_analysis || null })
}

export function fragmentReviewProblem(draft, content) {
  if (!draft.content?.trim()) return '请填写分析正文。'
  if (!draft.finding_refs.length && !draft.evidence_refs.length) return '至少保留一条已确认判断或一项资料依据。'
  if (draft.finding_refs.some(key => !content.findings.some(item => item.finding_key === key && item.status === 'CONFIRMED'))) {
    return '引用的判断尚未全部确认。请先审核，或修改正文并移除不采用的引用。'
  }
  if (draft.evidence_refs.some(key => !content.evidence.some(item => item.evidence_key === key && item.status === 'ACTIVE'))) {
    return '引用资料已更新，请重新运行 AI 分析。'
  }
  for (const record of [draft.framework_coverage, draft.structured_analysis].filter(Boolean)) {
    if (!record.quote?.trim() || !draft.content.includes(record.quote)) return '覆盖依据摘句必须逐字出现在当前正文中，请同步修改摘句。'
  }
  return ''
}
