const frequencyLabels = {
  daily: '每日',
  weekly: '每周',
  monthly: '每月',
  quarterly: '每季度'
}

export function resolveCalendarPracticeRefs(actionRefs, practiceRhythm) {
  const actions = new Map((practiceRhythm?.actions || []).map(action => [action.action_id, action]))
  return (Array.isArray(actionRefs) ? actionRefs : [])
    .map(ref => actions.get(ref))
    .filter(Boolean)
    .map(action => ({
      ...action,
      frequency_label: frequencyLabels[action.frequency] || '报告行动'
    }))
}
