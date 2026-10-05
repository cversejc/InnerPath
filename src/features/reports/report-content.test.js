import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeReportData } from './report-content.js'
import { createReportDocument } from './report-document-model.js'

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

test('delivered report fragments become readable chapters without exposing workflow metadata', () => {
  const report = normalizeReportData({
    id: 42,
    title: '辰鉴·人生说明书',
    basic_info: { name: '青鸟', report_date: '2026-10-04' },
    content_payload: {
      summary: '从一个可完成的小步开始。',
      structured_sections: [
        {
          section_key: 'identity',
          section_title: '你是谁',
          fragment_key: 'report.identity.psychic_structure',
          title: '内在驱动力',
          content: '你会先理解全局，再确认自己的立场。',
          revision_no: 3,
          sequence_no: 1
        },
        {
          section_key: 'challenge',
          section_title: '卡在哪',
          fragment_key: 'report.blocks.recurring_loop',
          title: '反复出现的循环',
          content: '准备很久以后，仍然需要一个小的现实反馈。',
          revision_no: 2,
          sequence_no: 2
        },
        {
          section_key: 'direction',
          section_title: '往哪去',
          fragment_key: 'report.direction.growth_experiments',
          title: '成长实验',
          content: '本周完成一页初稿，再根据反馈调整。',
          revision_no: 4,
          sequence_no: 3
        },
        {
          section_key: 'direction',
          section_title: '往哪去',
          fragment_key: 'report.ending',
          title: '带回日常',
          content: '每次多保留一点真实需求。',
          revision_no: 1,
          sequence_no: 4
        }
      ]
    }
  })

  const document = createReportDocument(report)
  const visibleDocument = JSON.stringify(document)

  assert.deepEqual(document.sections.map(section => section.title), [
    '你是谁', '卡在哪', '往哪去', '带回日常'
  ])
  assert.deepEqual(document.sections.map(section => section.blocks[0].title), [
    '内在驱动力', '反复出现的循环', '成长实验', '带回日常'
  ])
  assert.match(visibleDocument, /你会先理解全局/)
  assert.match(visibleDocument, /每次多保留一点真实需求/)
  assert.equal(document.summary.content, '从一个可完成的小步开始。')
  assert.doesNotMatch(visibleDocument, /report\.identity\.psychic_structure|report\.blocks\.recurring_loop/)
  assert.doesNotMatch(visibleDocument, /revision_no|sequence_no|section_key|fragment_key/)
  assert.ok(document.sections.every(section => section.readerPages.length > 0))
})
