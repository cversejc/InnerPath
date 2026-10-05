import assert from 'node:assert/strict'
import test from 'node:test'
import { buildReportDocument } from './report-document-model.js'
import { paginateMarkdownForReader } from './reader-pagination.js'

const withoutWhitespace = value => value.replace(/\s/g, '')

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

test('keeps the complete source for print while attaching screen reader fragments', () => {
  const markdown = `# 完整解读\n\n${'这是一段较长的报告内容。'.repeat(70)}`
  const document = buildReportDocument({}, { markdown })
  const section = document.sections.find(item => item.kind === 'markdown')

  assert.equal(section.content, markdown)
  assert.ok(section.readerPages.length > 1)
  assert.ok(section.readerPages.every(page => Array.from(page).length <= 600))
  assert.equal(withoutWhitespace(section.readerPages.join('\n\n')), withoutWhitespace(markdown))
})

test('keeps a bold numbered label with the first content on its continuation page', () => {
  const heading = '**② 练习“足够好就开始”**'
  const markdown = `${heading}\n\n${'先从一件小事开始，再根据真实感受调整。'.repeat(8)}`
  const pages = paginateMarkdownForReader(markdown, 90)

  assert.ok(pages.length > 1)
  assert.ok(pages[0].startsWith(heading))
  assert.ok(pages[0].length > heading.length)
})

test('keeps consecutive numbered headings together with their first list item', () => {
  const markdown = [
    '**1. 下属就可以做的 3 件事**',
    '',
    '**① 做一次能量流向记录**',
    '',
    '- 行动：连续 5 天记录一次当下的感受。',
    '- 完成标准：周末回看并总结。'
  ].join('\n')
  const pages = paginateMarkdownForReader(markdown, 90)

  assert.ok(pages[0].startsWith('**1. 下属就可以做的 3 件事**'))
  assert.ok(pages[0].includes('**① 做一次能量流向记录**'))
  assert.match(pages[0], /行动：/)
})
