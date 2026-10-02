import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeReportData } from './report-content.js'

test('new report projection renders authored sections while legacy reports stay readable', () => {
  const delivered = normalizeReportData({
    content_payload: {
      structured_sections: [
        {
          section_key: 'identity',
          section_title: '你是谁',
          fragment_key: 'report.identity',
          title: '稳定探索',
          content: '保留自己的节奏。'
        }
      ],
      summary: '从小步尝试开始。'
    }
  })
  const legacy = normalizeReportData({
    ai_raw_content: '## 历史报告\n原始内容继续展示。',
    energy_profile: { type: '综合型' }
  })

  assert.equal(delivered.structuredSections[0].fragment_key, 'report.identity')
  assert.equal(delivered.aiGeneratedContent, null)
  assert.equal(legacy.structuredSections, null)
  assert.equal(legacy.aiGeneratedContent, '## 历史报告\n原始内容继续展示。')
})
