import assert from 'node:assert/strict'
import test from 'node:test'
import { buildReportDocument, createReportDocument } from './report-document-model.js'
import { paginateMarkdownForReader } from './reader-pagination.js'
import { formatReportMarkdown } from './report-markdown.js'

const withoutWhitespace = value => value.replace(/\s/g, '')

function collectBlockText(blocks = []) {
  return blocks.map(block => [
    block.title,
    block.subtitle,
    block.content,
    ...(block.items || []),
    collectBlockText(block.children)
  ].join('\n')).join('\n')
}

test('splits long Markdown into reader pages without losing wording', () => {
  const markdown = [
    '# 核心观察',
    '',
    '先看见自己的节奏。'.repeat(9),
    '',
    '- 记录一次重要选择。',
    '- 留意当时的真实感受。',
    '',
    '为自己保留调整的空间。'.repeat(8)
  ].join('\n')

  const pages = paginateMarkdownForReader(markdown, 90)

  assert.ok(pages.length > 1)
  assert.ok(pages.every(page => Array.from(page).length <= 90))
  assert.match(pages[0], /^# 核心观察/)
  assert.equal(withoutWhitespace(pages.join('\n\n')), withoutWhitespace(markdown))
})

test('parses Markdown into ordered chapters and keeps nested heading levels', () => {
  const markdown = [
    '# 人生说明书 · 青鸟',
    '',
    '报告开篇。',
    '',
    '## 01 你是谁',
    '看见自己的稳定特质。',
    '### 世界看到的你',
    '外界感受到的部分。',
    '#### 第一层',
    '更细的观察。',
    '## 02 卡在哪',
    '正在面对的议题。',
    '### 重复出现的模式',
    '可以留意的模式。',
    '## 03 往哪去',
    '接下来可以尝试的方向。',
    '## 总结与寄语',
    '带回生活慢慢验证。'
  ].join('\n')

  const document = buildReportDocument({}, { markdown, reportTitle: '人生说明书 · 青鸟' })

  assert.deepEqual(document.sections.map(section => section.title), ['01 你是谁', '02 卡在哪', '03 往哪去'])
  const worldSection = document.sections[0].blocks.find(block => block.title === '世界看到的你')
  const firstLayer = worldSection.children.find(block => block.title === '第一层')
  assert.equal(worldSection.depth, 0)
  assert.equal(worldSection.content, '外界感受到的部分。')
  assert.equal(firstLayer.depth, 1)
  assert.equal(firstLayer.content, '更细的观察。')
  assert.equal(document.summary.title, '总结与寄语')
  assert.match(collectBlockText(document.sections[0].blocks), /报告开篇。/)
  assert.match(collectBlockText(document.sections[1].blocks), /重复出现的模式/)
  assert.match(collectBlockText(document.summary.blocks), /带回生活慢慢验证。/)
})

test('keeps a Markdown subsection title with the first content fragment', () => {
  const content = '先完成一小步，再根据实际反馈继续调整。'.repeat(80)
  const document = buildReportDocument({}, { markdown: `## 当前方向\n### 持续练习\n${content}` })
  const fragments = document.sections[0].readerPages.flatMap(page => page.blocks)
    .filter(block => block.title === '持续练习')

  assert.ok(fragments.length > 1)
  assert.ok(fragments.every(block => block.content))
  assert.equal(fragments[0].continued, false)
  assert.ok(fragments.slice(1).every(block => block.continued))
  assert.equal(withoutWhitespace(fragments.map(block => block.content).join('')), withoutWhitespace(content))
})

test('uses a generic report body when legacy Markdown has no headings', () => {
  const document = buildReportDocument({}, { markdown: '第一段内容。\n\n第二段内容。' })

  assert.equal(document.sections.length, 1)
  assert.equal(document.sections[0].title, '报告正文')
  assert.match(collectBlockText(document.sections[0].readerPages.flatMap(page => page.blocks)), /第二段内容。/)
})

test('uses the production report path to remove a duplicate cover heading', () => {
  const document = createReportDocument({
    title: '辰鉴·人生说明书 · 青鸟',
    basicInfo: { name: '青鸟' },
    aiGeneratedContent: '# 人生说明书 · 青鸟\n\n## 个人分析\n\n### 核心特质\n稳定而清晰的观察。'
  })

  assert.equal(document.title, '人生说明书 · 青鸟')
  assert.deepEqual(document.sections.map(section => section.title), ['个人分析'])
  assert.equal(document.sections[0].blocks[0].title, '核心特质')
  assert.equal(document.sections[0].blocks[0].content, '稳定而清晰的观察。')
})

test('omits empty Markdown and structured headings from chapters and contents', () => {
  const markdown = buildReportDocument({}, { markdown: '# 人生说明书\n\n## 空章节\n\n## 有内容的章节\n正文。', reportTitle: '人生说明书' })
  const structured = buildReportDocument({
    structuredSections: {
      empty: { title: '不应出现的标题', subsections: [{ title: '空小节' }] },
      filled: { title: '有效章节', subsections: [{ title: '有效小节', content: '有内容。' }] }
    }
  })

  assert.deepEqual(markdown.sections.map(section => section.title), ['有内容的章节'])
  assert.deepEqual(structured.sections.map(section => section.title), ['有效章节'])
  assert.deepEqual(structured.sections[0].blocks.map(block => block.title), ['有效小节'])
})

test('keeps reviewed structured content authoritative and labels unknown fields safely', () => {
  const document = buildReportDocument({
    structuredSections: {
      personal_analysis: {
        content: '审校后的内容。',
        subsections: [{ title: '核心特质', content: '真实结构内容。' }],
        unrecognized_internal_key: '保留字段的值。'
      },
      user_issues: [{ title: '用户议题', content: '议题正文。' }],
      summary: { title: '总结', content: '结构化总结。' }
    }
  }, { markdown: '# 不应混入正文\n\n未经审校的旧内容。' })

  const visible = [
    ...document.sections.map(section => `${section.title}\n${section.content}\n${collectBlockText(section.blocks)}`),
    document.summary.title,
    document.summary.content
  ].join('\n')

  assert.deepEqual(document.sections.map(section => section.title), ['个人分析', '用户议题'])
  assert.match(visible, /审校后的内容。/)
  assert.doesNotMatch(visible, /未经审校/)
  assert.match(visible, /补充内容/)
  assert.match(visible, /保留字段的值。/)
  assert.doesNotMatch(visible, /unrecognized_internal_key/)
  assert.doesNotMatch(visible, /未经审校的旧内容/)
})

test('renders action experiments, comparisons, tags and timeline metadata from explicit structure', () => {
  const document = buildReportDocument({
    structuredSections: {
      topics: [{
        title: '行动与观察',
        subsections: [
          { title: '小步实验', area: '表达练习', action: '完成一份小作品。', timeline: '本周' },
          { title: '变化对照', before: '反复准备', after: '先完成初稿' },
          { title: '支持资源', display_type: 'tags', items: ['记录', '反馈'] },
          { title: '阶段地图', display_type: 'timeline', stages: [{ title: '试做', content: '先完成小步。' }] },
          { title: '决策自检', items: ['是否符合当前目标？'] }
        ]
      }]
    }
  })
  const blocks = document.sections[0].blocks

  assert.equal(blocks[0].displayType, 'action')
  assert.deepEqual(blocks[0].metadata, [{ label: '时间', value: '本周' }])
  assert.equal(blocks[1].displayType, 'comparison')
  assert.deepEqual(blocks[1].comparison, { fromLabel: '之前', from: '反复准备', toLabel: '之后', to: '先完成初稿' })
  assert.equal(blocks[2].displayType, 'tags')
  assert.equal(blocks[3].displayType, 'timeline')
  assert.equal(blocks[3].children[0].title, '试做')
  assert.equal(blocks[4].displayType, 'checklist')

  const comparisonSection = buildReportDocument({
    structuredSections: {
      transition: { title: '关键转变', before: '持续准备', after: '开始尝试' }
    }
  }).sections[0]
  assert.equal(comparisonSection.title, '关键转变')
  assert.equal(comparisonSection.readerPages[0].blocks[0].comparison.from, '持续准备')

  const comparisonSummary = buildReportDocument({
    structuredSections: {
      summary: { title: '总结', before: '沿用旧方法', after: '尝试新选择' }
    }
  }).summary
  assert.equal(comparisonSummary.readerPages[0].blocks[0].comparison.to, '尝试新选择')
})

test('paginates structured sections with anchors and preserves all long content', () => {
  const content = '每次只做一件小事，并记录真实反馈。'.repeat(70)
  const document = buildReportDocument({
    structuredSections: {
      topics: [{
        title: '行动练习',
        subsections: [{ title: '第一步', content }]
      }]
    }
  })
  const section = document.sections[0]
  const pages = section.readerPages
  const fragments = pages.flatMap(page => page.blocks)

  assert.ok(pages.length > 1)
  assert.ok(fragments.every(block => block.anchorId))
  assert.ok(fragments.some(block => block.continued))
  assert.equal(withoutWhitespace(fragments.map(block => block.content).join('')), withoutWhitespace(content))
})

test('formats nested headings, lists, quotes and explicit arrow flows safely', () => {
  const html = formatReportMarkdown([
    '### 具体观察',
    '##### 更深层级',
    '',
    '> 先确认自己的真实感受。',
    '',
    '- [x] 记录一次选择',
    '- [ ] 回看选择结果',
    '',
    '观察 → 记录 → 调整',
    '',
    '<script>alert(1)</script>'
  ].join('\n'))

  assert.match(html, /<h5>具体观察<\/h5>/)
  assert.match(html, /<h5>更深层级<\/h5>/)
  assert.doesNotMatch(html, /<h6>/)
  assert.match(html, /<blockquote>/)
  assert.match(html, /report-checklist/)
  assert.match(html, /report-inline-flow/)
  assert.match(html, /&lt;script&gt;/)
  assert.doesNotMatch(html, /<script>/)
})
