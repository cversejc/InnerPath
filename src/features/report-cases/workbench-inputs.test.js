import test from 'node:test'
import assert from 'node:assert/strict'
import { reportFragmentTitle, reportStage, REPORT_WORKFLOW_STAGES } from './stages.js'
import {
  buildWorkbenchInputGroups,
  buildWorkbenchStageOutputs,
  classifyWorkbenchStepView,
  formatConsultantEvidenceValue,
  isVisibleConsultantEvidence,
  reportEvidenceTitle,
  qualitySummaryLabel,
  currentReportFoundation,
  visibleConsultantEvidence
} from './workbench-inputs.js'

function makeCase(currentStep = 'S1') {
  return {
    application_snapshot: {
      profile: {
        name: '林女士',
        gender: 'female',
        birth_year: 1991,
        birth_month: 9,
        birth_day: 22,
        birth_hour: 9,
        birth_minute: 10,
        birth_place: '杭州',
        calendar_type: 'solar',
        time_accuracy: 'exact'
      },
      context: {
        focus_topics: ['career', 'self'],
        current_challenge: '在稳定岗位和内部转岗之间犹豫。',
        profile_version: 3
      },
      additional_info: '希望先通过访谈和小任务验证新方向。'
    },
    workflow_instance: {
      steps: [
        { id: 1, step_key: 'S1', sequence_no: 1 },
        { id: 2, step_key: 'S2', sequence_no: 2 },
        { id: 3, step_key: 'S3', sequence_no: 3 },
        { id: 4, step_key: 'S4', sequence_no: 4 },
        { id: 5, step_key: 'S5', sequence_no: 5 },
        { id: 6, step_key: 'S6', sequence_no: 6 }
      ].map(step => ({ ...step, status: step.step_key === currentStep ? 'IN_REVIEW' : 'COMPLETED' }))
    }
  }
}

const sourceEvidence = {
  evidence_key: 'input.context.current_challenge',
  source_type: 'USER_PROVIDED',
  status: 'ACTIVE',
  value_json: '在稳定岗位和内部转岗之间犹豫。'
}

const foundationFinding = {
  finding_key: 'foundation.structure',
  claim: '用户在改变工作方式前倾向先建立可预期的边界。',
  status: 'CONFIRMED',
  semantic_role: 'RESOURCE',
  confidence: 'MEDIUM',
  evidence_refs: [sourceEvidence.evidence_key],
  owner_step_task_id: 1
}

test('every report step exposes a task, concrete inputs, and consultant tools', () => {
  assert.equal(REPORT_WORKFLOW_STAGES.length, 6)
  for (const stage of REPORT_WORKFLOW_STAGES) {
    assert.ok(stage.task, `${stage.stepKey} should explain its task`)
    assert.ok(stage.actions.length >= 3, `${stage.stepKey} should give actionable steps`)
    assert.ok(stage.inputGuidance, `${stage.stepKey} should explain what inputs mean`)
    assert.ok(stage.inputGroups.length, `${stage.stepKey} should show available inputs`)
    assert.ok(stage.inputGroups.every(group => group.reason), `${stage.stepKey} should explain why each input matters`)
    assert.ok(stage.tools.length, `${stage.stepKey} should expose useful tools`)
    assert.ok(stage.checklist.length, `${stage.stepKey} should list completion checks`)
  }
})

test('collection reading retains complete confirmed prose and its originating node', () => {
  const prose = '已确认的分析内容。'.repeat(60) + '完整结尾不能被概览截断。'
  const content = { findings: [foundationFinding], evidence: [], fragments: [
    { fragment_key: 'analysis.s1.complete', fragment_type: 'ANALYSIS', status: 'CONFIRMED', owner_step_task_id: 1, content: prose, title: '前序分析' },
    { fragment_key: 'report.identity.outer_self', fragment_type: 'REPORT', status: 'CONFIRMED', owner_step_task_id: 5, content: prose, title: '完整正文' },
    { fragment_key: 'unreviewed', fragment_type: 'REPORT', status: 'PROPOSED', owner_step_task_id: 5, content: '未审核内容' }
  ] }
  const s3 = buildWorkbenchInputGroups({ stage: reportStage('S3'), reportCase: makeCase('S3'), content })
  const analysis = s3.find(group => group.key === 'upstreamFragments')
  assert.equal(analysis.continuous, true)
  assert.equal(analysis.items[0].body, prose)
  assert.equal(analysis.items[0].origin, '第 1 步')
  assert.equal(s3.find(group => group.key === 'upstreamFindings').items[0].origin, '第 1 步')
  const report = buildWorkbenchInputGroups({ stage: reportStage('S6'), reportCase: makeCase('S6'), content }).find(group => group.key === 'reportFragments')
  assert.equal(report.items.length, 1)
  assert.equal(report.items[0].body, prose)
  assert.equal(report.items[0].origin, '第 5 步')
})

test('report continuous reading follows the confirmed plan and retains unplanned confirmed sections', () => {
  const fragments = ['report.ending', 'report.overview.psychic_structure', 'report.direction.life_map', 'custom.appendix'].map(fragment_key => ({ fragment_key, fragment_type: 'REPORT', status: 'CONFIRMED', content: fragment_key }))
  const makeGroups = narrativePlan => buildWorkbenchInputGroups({ stage: reportStage('S6'), reportCase: makeCase('S6'), content: { fragments }, narrativePlan }).find(group => group.key === 'reportFragments').items.map(item => item.key)
  assert.deepEqual(makeGroups(null), ['report.overview.psychic_structure', 'report.direction.life_map', 'report.ending', 'custom.appendix'])
  const narrativePlan = { plan_json: { content_plan: { fragments: [{ fragment_key: 'report.direction.life_map' }, { fragment_key: 'report.overview.psychic_structure' }, { fragment_key: 'report.ending' }] } } }
  assert.deepEqual(makeGroups(narrativePlan), ['report.direction.life_map', 'report.overview.psychic_structure', 'report.ending', 'custom.appendix'])
  assert.equal(fragments[0].fragment_key, 'report.ending')
})

test('report fragment headings are presented in Chinese', () => {
  assert.equal(reportFragmentTitle('report.overview.psychic_structure', 'psychic structure'), '整体心灵结构')
  assert.equal(reportFragmentTitle('report.identity.hidden_self', 'hidden self'), '被隐藏的自己')
  assert.equal(reportFragmentTitle('report.identity.outer_self', '在连接中留出边界'), '在连接中留出边界')
  assert.equal(reportFragmentTitle('report.unknown', 'unknown title'), '报告段落')
})

test('S1 application inputs stay separate from its calculation workspace', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S1'),
    reportCase: makeCase('S1'),
    content: {
      evidence: [
        sourceEvidence,
        { evidence_key: 'system.bazi', source_type: 'SYSTEM_CALCULATED', status: 'ACTIVE', value_json: { day_master: '甲木', note: '仅供专业参考' } }
      ],
      findings: [],
      fragments: []
    }
  })

  assert.deepEqual(groups.map(group => group.key), ['profile', 'context'])
  assert.equal(groups[0].items.find(item => item.title === '出生日期')?.body, '1991 年 9 月 22 日')
  assert.equal(groups[1].items.find(item => item.title === '本次主要困扰')?.body, '在稳定岗位和内部转岗之间犹豫。')
  assert.equal(groups[1].items.some(item => item.body.includes('profile_version')), false)
})

test('S1 selects only the current mingli-v2 foundation evidence', () => {
  const system = {
    id: 70,
    evidence_key: 'calculated.mingli_foundation.v2',
    source_type: 'SYSTEM_CALCULATED',
    status: 'ACTIVE',
    created_at: '2026-10-01T00:00:00Z',
    value_json: {
      calculation_version: 'mingli-v2',
      bazi: { year: { stem: '辛', branch: '未' } }
    }
  }
  const duplicate = {
    ...system,
    id: 71,
    evidence_key: 'calculated.mingli_foundation.v2.r2',
    created_at: '2026-10-02T00:00:00Z'
  }
  const legacy = {
    id: 72,
    evidence_key: 'system.bazi',
    source_type: 'SYSTEM_CALCULATED',
    status: 'ACTIVE',
    value_json: { bazi: { day_master: '乙' } }
  }
  const correction = {
    id: 73,
    evidence_key: 'calculated.mingli_foundation.consultant.1',
    source_type: 'CONSULTANT_CORRECTED',
    status: 'ACTIVE',
    created_at: '2026-10-03T00:00:00Z',
    value_json: {
      calculation_version: 'mingli-v2',
      bazi: { year: { stem: '壬', branch: '申' } }
    }
  }

  assert.equal(currentReportFoundation([legacy, system, duplicate]), duplicate)
  assert.equal(currentReportFoundation([system, correction]), correction)
  assert.deepEqual(
    visibleConsultantEvidence([legacy, system, duplicate, correction]),
    [correction]
  )
})

test('evidence references use consultant-readable names instead of list numbers or raw keys', () => {
  assert.equal(reportEvidenceTitle({ evidence_key: 'input.profile.birth_day', source_type: 'USER_PROVIDED' }), '出生日')
  assert.equal(reportEvidenceTitle({ evidence_key: 'input.context.current_challenge', source_type: 'USER_PROVIDED' }), '本次主要困扰')
  assert.equal(reportEvidenceTitle({ evidence_key: 'calculated.mingli_foundation.v1', source_type: 'SYSTEM_CALCULATED' }), '命理测算依据')
})

test('application context hides internal profile identifiers instead of presenting them as user details', () => {
  const reportCase = makeCase('S1')
  reportCase.application_snapshot.context.user_profile_id = 14
  reportCase.application_snapshot.context.profile_id = 14
  reportCase.application_snapshot.context.profile_version = 3
  reportCase.application_snapshot.context.user_profile = 14
  reportCase.application_snapshot.context.profile = 14
  reportCase.application_snapshot.context.user = 14
  reportCase.application_snapshot.context.record = 14
  reportCase.application_snapshot.context.created_at = '2026-10-03'

  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S1'),
    reportCase,
    content: { evidence: [], findings: [], fragments: [] }
  })

  assert.equal(groups[1].items.some(item => item.body === '14'), false)
  assert.deepEqual(groups[1].items.map(item => item.title), ['关注主题', '本次主要困扰', '补充说明'])
})

test('evidence details hide internal identifiers, including nested profile IDs', () => {
  const rendered = formatConsultantEvidenceValue({
    user_profile_id: 14,
    profile_version: 3,
    created_at: '2026-10-03',
    current_challenge: '在稳定岗位和内部转岗之间犹豫。',
    profile: { id: 14, name: '林女士' }
  })

  assert.doesNotMatch(rendered, /14|profile_version|created_at/)
  assert.match(rendered, /本次主要困扰：在稳定岗位和内部转岗之间犹豫。/)
  assert.match(rendered, /称呼：林女士/)
  assert.equal(isVisibleConsultantEvidence({ evidence_key: 'input.context.user_profile_id' }), false)
  assert.equal(isVisibleConsultantEvidence({ evidence_key: 'input.context.created_at' }), false)
  assert.equal(isVisibleConsultantEvidence({ evidence_key: 'input.context.current_challenge' }), true)
})

test('S2 only receives confirmed findings from the preceding step and their sources', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S2'),
    reportCase: makeCase('S2'),
    content: {
      evidence: [sourceEvidence],
      findings: [
        foundationFinding,
        { ...foundationFinding, finding_key: 'unreviewed', claim: '待审核判断', status: 'PROPOSED', owner_step_task_id: 1 },
        { ...foundationFinding, finding_key: 'future', claim: '后续步骤判断', owner_step_task_id: 3 }
      ],
      fragments: []
    }
  })

  assert.equal(groups[1].items.length, 1)
  assert.equal(groups[1].items[0].title, foundationFinding.claim)
  assert.equal(groups[2].items[0].title, '本次主要困扰')
  assert.equal(groups[2].items[0].body, sourceEvidence.value_json)
})

test('S3 and S4 only receive findings confirmed in preceding steps', () => {
  const findings = [
    { ...foundationFinding, finding_key: 's1', claim: '判断 s1', owner_step_task_id: 1 },
    { ...foundationFinding, finding_key: 's2', claim: '判断 s2', owner_step_task_id: 2 },
    { ...foundationFinding, finding_key: 's3', claim: '判断 s3', owner_step_task_id: 3 },
    { ...foundationFinding, finding_key: 's4', claim: '判断 s4', owner_step_task_id: 4 },
    { ...foundationFinding, finding_key: 's5', claim: '判断 s5', owner_step_task_id: 5 }
  ]
  const makeInputs = stepKey => {
    const groups = buildWorkbenchInputGroups({
      stage: reportStage(stepKey),
      reportCase: makeCase(stepKey),
      content: { evidence: [], findings, fragments: [] }
    })
    return groups[stepKey === 'S4' ? 1 : 0].items.map(item => item.title)
  }

  assert.deepEqual(makeInputs('S3'), ['判断 s1', '判断 s2'])
  assert.deepEqual(makeInputs('S4'), ['判断 s1', '判断 s2', '判断 s3'])
})

test('S6 only shows report fragments confirmed for final review', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S6'),
    reportCase: makeCase('S6'),
    content: {
      evidence: [],
      findings: [foundationFinding],
      fragments: [
        { fragment_key: 'report.identity', title: '确认段落', content: '可交付内容', fragment_type: 'REPORT', status: 'CONFIRMED' },
        { fragment_key: 'report.draft', title: '未确认段落', content: '待审核内容', fragment_type: 'REPORT', status: 'PROPOSED' }
      ]
    }
  })

  assert.deepEqual(groups[0].items.map(item => item.title), ['确认段落'])
})

test('S5 displays confirmed semantic assets, the selected narrative, and the writing plan', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S5'),
    reportCase: makeCase('S5'),
    content: {
      evidence: [sourceEvidence],
      findings: [foundationFinding, { ...foundationFinding, finding_key: 'proposal', status: 'PROPOSED' }],
      fragments: [{
        fragment_key: 'analysis.core',
        fragment_type: 'ANALYSIS',
        title: '当前工作选择',
        content: '先通过低成本访谈理解转岗后的实际工作，再评估是否继续。',
        status: 'CONFIRMED',
        owner_step_task_id: 4,
        source_snapshot: { findings: [{ finding_key: foundationFinding.finding_key, claim: foundationFinding.claim }] }
      }]
    },
    narrativePlan: {
      id: 8,
      status: 'CONFIRMED',
      plan_json: {
        core_theme: '先用可逆的小尝试验证方向，再决定是否转岗。',
        must_include_findings: [foundationFinding.finding_key],
        content_plan: { fragments: [{ fragment_key: 'report.direction', title: '下一步尝试', purpose: '安排一次行业访谈。', finding_refs: [foundationFinding.finding_key] }] }
      }
    }
  })

  assert.equal(groups[0].items.length, 1)
  assert.equal(groups[0].items[0].title, foundationFinding.claim)
  assert.equal(groups[1].items[0].title, '当前工作选择')
  assert.match(groups[2].items[0].title, /先用可逆的小尝试/)
  assert.equal(groups[3].items[0].title, '下一步尝试')
})

test('S5 stage results resolve report sources to readable findings and evidence', () => {
  const outputs = buildWorkbenchStageOutputs({
    stage: reportStage('S5'),
    reportCase: makeCase('S5'),
    content: {
      evidence: [sourceEvidence],
      findings: [foundationFinding],
      fragments: [{
        fragment_key: 'report.direction',
        fragment_type: 'REPORT',
        title: '下一步尝试',
        content: '先完成一次从业者访谈。',
        status: 'PROPOSED',
        owner_step_task_id: 5,
        source_snapshot: {
          findings: [{ finding_key: foundationFinding.finding_key }],
          evidence: [{ evidence_key: sourceEvidence.evidence_key }]
        }
      }]
    }
  })

  assert.match(outputs[0].source, /用户在改变工作方式前倾向先建立可预期的边界/)
  assert.match(outputs[0].source, /本次主要困扰/)
  assert.doesNotMatch(outputs[0].source, /foundation\.structure|input\.context/)
})

test('S6 shows report copy and open quality findings', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S6'),
    reportCase: makeCase('S6'),
    content: {
      evidence: [sourceEvidence],
      findings: [foundationFinding],
      fragments: [{ fragment_key: 'report.direction', fragment_type: 'REPORT', title: '下一步尝试', content: '先完成一次从业者访谈。', status: 'CONFIRMED' }]
    },
    quality: {
      quality_status: 'PROGRAMMATIC_BLOCKED',
      issues: [{ id: 19, severity: 'BLOCK', status: 'OPEN', message: '报告中有一句话没有对应的已确认判断。', suggestion: '补充来源或删除该句。' }]
    }
  })

  assert.equal(groups[0].items[0].body, '先完成一次从业者访谈。')
  const qualityIssue = groups.find(group => group.key === 'qualityIssues').items[0]
  assert.match(qualityIssue.meta, /必须处理/)
  assert.equal(qualityIssue.body, '补充来源或删除该句。')
})

test('S6 explains repeated semantic references without exposing internal finding keys', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S6'),
    reportCase: makeCase('S6'),
    content: { evidence: [], findings: [], fragments: [] },
    quality: {
      quality_status: 'PASSED',
      issues: [{
        id: 20,
        severity: 'MINOR',
        status: 'OPEN',
        issue_type: 'FINDING_OVER_REPEATED',
        message: 'Finding s3.integration.central_tension_certainty_vs_agency 在 5 个报告片段中重复出现。',
        suggestion: '检查重复表达。'
      }]
    }
  })

  const qualityIssue = groups.find(group => group.key === 'qualityIssues').items[0]
  assert.equal(qualityIssue.title, '同一专业判断被多段引用')
  assert.match(qualityIssue.body, /各段是否各自承担不同作用/)
  assert.match(qualityIssue.meta, /建议复核/)
  assert.doesNotMatch(JSON.stringify(qualityIssue), /central_tension|Finding s3/)
})

test('completed quality checks show the open work instead of an unrun state', () => {
  assert.equal(qualitySummaryLabel({
    quality_status: 'COMPLETED',
    open_count: 15,
    latest_validator_run: { status: 'COMPLETED' }
  }), '检查完成 · 15 项待处理')
  assert.equal(qualitySummaryLabel({
    quality_status: 'COMPLETED',
    open_count: 0,
    can_approve: true,
    latest_validator_run: { status: 'COMPLETED' }
  }), '可以进入最终复核')
})

test('quality issues use clear Chinese action labels and severity levels', () => {
  const groups = buildWorkbenchInputGroups({
    stage: reportStage('S6'),
    reportCase: makeCase('S6'),
    content: {
      evidence: [],
      findings: [],
      fragments: [{ fragment_key: 'report.identity.outer_self', title: '当前职业处境' }]
    },
    quality: {
      quality_status: 'COMPLETED',
      issues: [{
        id: 31,
        issue_type: 'report_coherence',
        target_fragment_key: 'report.identity.outer_self',
        severity: 'MAJOR',
        status: 'OPEN',
        message: 'report.identity.outer_self 与 report.identity.hidden_self 不一致。',
        suggestion: '重新审阅 report.identity.outer_self。'
      }]
    }
  })

  const issue = groups.find(group => group.key === 'qualityIssues').items[0]
  assert.equal(issue.title, '当前职业处境 · 报告表达需要复核')
  assert.match(issue.body, /统一叙述方式/)
  assert.match(issue.meta, /需要处理 · 待处理/)
  assert.doesNotMatch(JSON.stringify(issue), /report\.identity|report_coherence/)
})

test('step navigation distinguishes current work, completed history, and locked future previews', () => {
  const current = { id: 2, sequence_no: 2, status: 'IN_REVIEW' }
  assert.equal(classifyWorkbenchStepView(current, current), 'CURRENT')
  assert.equal(classifyWorkbenchStepView({ id: 1, sequence_no: 1, status: 'COMPLETED' }, current), 'HISTORY')
  assert.equal(classifyWorkbenchStepView({ id: 3, sequence_no: 3, status: 'PENDING' }, current), 'UPCOMING')
  assert.equal(classifyWorkbenchStepView({ id: 2, sequence_no: 2, status: 'COMPLETED' }, null), 'HISTORY')
})

test('stage results include completed suggestions that have not yet entered human review', () => {
  const reportCase = makeCase('S1')
  const step = reportCase.workflow_instance.steps[0]
  step.activation_no = 1
  const outputs = buildWorkbenchStageOutputs({
    stage: reportStage('S1'),
    reportCase,
    content: { evidence: [sourceEvidence], findings: [], fragments: [] },
    analysisRuns: [{
      id: 91,
      target_type: 'REPORT_ANALYSIS_DRAFT',
      target_key: 'S1',
      status: 'COMPLETED',
      context_snapshot: { analysis_activation_no: 1 },
      output_parsed: {
        findings: [{
          finding_key: 'career.pattern',
          claim: '面对职业变化时，先确认可控条件有助于减轻反复比较。',
          kind: 'FINDING',
          confidence: 'MEDIUM',
          evidence_refs: [sourceEvidence.evidence_key]
        }],
        analysis_fragments: []
      }
    }]
  })

  assert.equal(outputs.length, 1)
  assert.match(outputs[0].meta, /专业判断建议/)
  assert.match(outputs[0].body, /尚未加入审核/)
  assert.match(outputs[0].source, /本次主要困扰/)
})
