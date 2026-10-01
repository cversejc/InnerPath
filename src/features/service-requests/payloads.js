function clone(value) {
  return value ? JSON.parse(JSON.stringify(value)) : value
}

function splitList(value) {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean)
  return String(value || '').split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
}

function listText(value) {
  return Array.isArray(value) ? value.join('\n') : String(value || '')
}

export function reportEditorFromPayload(payload = {}) {
  const energy = payload.energy_profile || {}
  const career = payload.career_guidance || {}
  const relationship = payload.relationship_pattern || {}
  const growth = payload.personal_growth || {}
  const actionPlan = (growth.action_plan || []).map(item => typeof item === 'string'
    ? item
    : [item.area, item.action, item.timeline].filter(Boolean).join(' · '))

  return {
    title: payload.title || '辰鉴·人生说明书',
    energy: {
      type: energy.type || '',
      core_traits: energy.core_traits || energy.coreTraits || '',
      description: energy.description || ''
    },
    career: {
      suitable_paths: listText(career.suitable_paths || career.suitablePaths),
      work_style: career.work_style || career.workStyle || '',
      development_suggestions: listText(career.development_suggestions || career.developmentSuggestions)
    },
    relationship: {
      style: relationship.style || '',
      strengths: listText(relationship.strengths),
      challenges: listText(relationship.challenges),
      growth_direction: relationship.growth_direction || relationship.growthDirection || ''
    },
    growth: {
      current_issues: listText(growth.current_issues || growth.currentIssues),
      action_plan: actionPlan.join('\n'),
      resources: listText(growth.resources)
    },
    summary: payload.summary || ''
  }
}

export function calendarEditorFromPayload(payload = {}) {
  const meta = payload.meta_payload || {}
  return {
    title: payload.title || '辰鉴·你的决策时机说明书',
    start_date: payload.start_date || '',
    end_date: payload.end_date || '',
    meta_payload: { ...meta, rhythm: meta.rhythm || '', intro: meta.intro || '' },
    entries: (payload.entries || []).map((entry, index) => ({
      ...clone(entry),
      _key: `${entry.entry_date || 'entry'}-${index}-${Math.random().toString(36).slice(2, 7)}`,
      suitableText: listText(entry.suitable),
      unsuitableText: listText(entry.unsuitable)
    }))
  }
}

export function buildReportPayload(current = {}, editor) {
  return {
    ...clone(current),
    title: editor.title,
    energy_profile: {
      ...current.energy_profile,
      type: editor.energy.type,
      core_traits: editor.energy.core_traits,
      description: editor.energy.description
    },
    career_guidance: {
      ...current.career_guidance,
      suitable_paths: splitList(editor.career.suitable_paths),
      work_style: editor.career.work_style,
      development_suggestions: splitList(editor.career.development_suggestions)
    },
    relationship_pattern: {
      ...current.relationship_pattern,
      style: editor.relationship.style,
      strengths: splitList(editor.relationship.strengths),
      challenges: splitList(editor.relationship.challenges),
      growth_direction: editor.relationship.growth_direction
    },
    personal_growth: {
      ...current.personal_growth,
      current_issues: splitList(editor.growth.current_issues),
      action_plan: splitList(editor.growth.action_plan).map(action => ({
        area: '咨询师审校',
        action,
        timeline: '按个人节奏推进'
      })),
      resources: splitList(editor.growth.resources)
    },
    summary: editor.summary
  }
}

export function buildCalendarPayload(current = {}, editor) {
  return {
    ...clone(current),
    title: editor.title,
    start_date: editor.start_date,
    end_date: editor.end_date,
    meta_payload: clone(editor.meta_payload),
    entries: editor.entries.map(entry => ({
      entry_date: entry.entry_date,
      day_pillar: entry.day_pillar || null,
      tone: entry.tone || null,
      status_label: entry.status_label || null,
      keyword: entry.keyword || null,
      summary: entry.summary || null,
      suitable: splitList(entry.suitableText),
      unsuitable: splitList(entry.unsuitableText),
      time_window: entry.time_window || null,
      admin_note: entry.admin_note || null
    }))
  }
}
