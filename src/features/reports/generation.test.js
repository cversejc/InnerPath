import assert from 'node:assert/strict'
import test from 'node:test'
import apiClient from '../../utils/apiClient.js'
import { buildReportRequest, generateReportWithAI } from './generation.js'

test('report request mapping normalizes the current assessment context', () => {
  assert.deepEqual(buildReportRequest({
    profile_version: '3',
    context: {
      focus_topics: ['职业方向'],
      current_challenge: ' 转型选择 ',
      expected_outcomes: ['明确方向']
    }
  }), {
    profile_version: 3,
    context: {
      focus_topics: ['职业方向'],
      current_challenge: '转型选择',
      expected_outcomes: ['明确方向'],
      issue_duration: null,
      impact_level: null,
      decision_status: null,
      decision_description: null,
      decision_style: [],
      additional_info: null
    }
  })
})

test('generation submits a task, polls it, and formats its completed report', async () => {
  const originalGet = apiClient.get
  const originalPost = apiClient.post
  const originalSetTimeout = globalThis.setTimeout
  const requests = []
  const report = {
    id: 42,
    basic_info: { name: '林一' },
    energy_profile: { type: '专注型' },
    career_guidance: { suitable_paths: ['研究'], work_style: '独立' },
    summary: '报告摘要'
  }

  apiClient.post = async (url, data) => {
    requests.push(['post', url, data])
    return { data: { task_id: 21 } }
  }
  apiClient.get = async url => {
    requests.push(['get', url])
    if (url === '/reports/tasks/21') {
      return { data: { status: 'completed', report_id: 42 } }
    }
    return { data: report }
  }
  globalThis.setTimeout = callback => {
    queueMicrotask(callback)
    return 0
  }

  try {
    const result = await generateReportWithAI({ profile_version: 3, context: {} })
    assert.deepEqual(requests, [
      ['post', '/reports', {
        profile_version: 3,
        context: {
          focus_topics: [],
          current_challenge: null,
          expected_outcomes: [],
          issue_duration: null,
          impact_level: null,
          decision_status: null,
          decision_description: null,
          decision_style: [],
          additional_info: null
        }
      }],
      ['get', '/reports/tasks/21'],
      ['get', '/reports/42']
    ])
    assert.equal(result.id, 42)
    assert.deepEqual(result.basicInfo, { name: '林一' })
    assert.deepEqual(result.careerGuidance, {
      suitablePaths: ['研究'],
      workStyle: '独立',
      developmentSuggestions: []
    })
    assert.equal(result.summary, '报告摘要')
  } finally {
    apiClient.get = originalGet
    apiClient.post = originalPost
    globalThis.setTimeout = originalSetTimeout
  }
})
