function normalizedTitle(value) {
  return String(value || '')
    .replace(/^辰鉴\s*[·・]?\s*/, '')
    .replace(/[\s·・《》【】、，,：:。.!！?？]/g, '')
    .toLowerCase()
}

function isCoverTitle(value, reportTitle) {
  const heading = normalizedTitle(value)
  if (!heading) return false
  const title = normalizedTitle(reportTitle)
  return heading === title
    || heading === '人生说明书'
    || (heading.startsWith('人生说明书') && title.startsWith('人生说明书') && (heading.startsWith(title) || title.startsWith(heading)))
    || (heading === '人生说明书' && title.startsWith('人生说明书'))
}

function isSummaryTitle(value) {
  return /^(总结(?:与寄语)?|结语|结束语|最后想对你说)$/.test(String(value || '').replace(/[\s·・]/g, ''))
}

function createBodyBlock(lines, id) {
  const content = lines.join('\n').trim()
  if (!content) return null
  return { id, title: '', subtitle: '', content, items: [], children: [] }
}

function pruneEmptyBlocks(blocks) {
  return blocks.map(block => ({
    ...block,
    children: pruneEmptyBlocks(block.children || []),
    blocks: pruneEmptyBlocks(block.blocks || [])
  })).filter(block => Boolean(
    String(block.content || '').trim()
    || block.items?.some(item => String(item || '').trim())
    || block.children?.length
    || block.blocks?.length
  ))
}

/** Convert legacy Markdown headings into the same ordered chapter tree used by structured reports. */
export function parseReportMarkdownStructure(markdown, { reportTitle = '' } = {}) {
  const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n')
  const firstContentLine = lines.findIndex(line => line.trim())
  if (firstContentLine >= 0) {
    const firstHeading = lines[firstContentLine].match(/^\s*#{1,6}\s+(.+?)\s*#*\s*$/)
    if (firstHeading && isCoverTitle(firstHeading[1], reportTitle)) lines.splice(firstContentLine, 1)
  }

  const headingLines = lines.map((line, index) => ({
    index,
    match: line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/)
  })).filter(item => item.match)
  const rootLevel = headingLines.length
    ? Math.min(...headingLines.map(item => item.match[1].length))
    : null
  const hadMarkdownHeadings = headingLines.length > 0
  const sections = []
  let summary = null
  let headingStack = []
  let bodyLines = []
  let blockSequence = 0
  let sectionSequence = 0
  let leadingBlocks = []

  const appendBody = () => {
    const content = bodyLines.join('\n').trim()
    bodyLines = []
    if (!content) return
    const parent = headingStack.at(-1)?.node
    if (!parent) {
      leadingBlocks.push(createBodyBlock([content], `markdown-body-${++blockSequence}`))
      return
    }
    if (parent.kind === 'markdown' || parent.kind === 'summary-source') {
      parent.blocks.push(createBodyBlock([content], `markdown-body-${++blockSequence}`))
    } else {
      parent.content = [parent.content, content].filter(Boolean).join('\n\n')
    }
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index]
    const match = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/)
    if (!match) {
      bodyLines.push(line)
      continue
    }

    appendBody()
    const level = match[1].length
    const title = match[2].trim()
    if (level === rootLevel || !headingStack.length) {
      const node = {
        id: `markdown-section-${++sectionSequence}`,
        title,
        subtitle: '',
        content: '',
        items: [],
        blocks: [],
        kind: 'markdown'
      }
      if (isSummaryTitle(title) && !summary) {
        node.kind = 'summary-source'
        summary = node
      } else {
        sections.push(node)
      }
      if (leadingBlocks.length) {
        node.blocks.push(...leadingBlocks)
        leadingBlocks = []
      }
      headingStack = [{ node, level }]
      continue
    }

    while (headingStack.length > 1 && headingStack.at(-1).level >= level) headingStack.pop()
    const parent = headingStack.at(-1)?.node
    if (!parent) continue
    const effectiveLevel = Math.min(level, headingStack.at(-1).level + 1)
    const node = {
      id: `markdown-block-${++blockSequence}`,
      title,
      subtitle: '',
      content: '',
      items: [],
      children: [],
      depth: headingStack.length - 1,
    }
    if (parent.kind === 'markdown' || parent.kind === 'summary-source') parent.blocks.push(node)
    else parent.children.push(node)
    headingStack.push({ node, level: effectiveLevel })
  }

  appendBody()

  if (summary) {
    summary.blocks = pruneEmptyBlocks(summary.blocks)
    summary = {
      title: summary.title,
      content: summary.content,
      items: summary.items,
      blocks: summary.blocks
    }
    if (!summary.content && !summary.items.length && !summary.blocks.length) summary = null
  }

  const visibleSections = sections.map(section => ({
    ...section,
    blocks: pruneEmptyBlocks(section.blocks)
  })).filter(section => String(section.content || '').trim() || section.items?.length || section.blocks.length)

  if (!hadMarkdownHeadings && !visibleSections.length && !summary) {
    const body = createBodyBlock(lines, `markdown-body-${++blockSequence}`)
    if (body) {
      visibleSections.push({
        id: 'markdown-section-1',
        title: '报告正文',
        subtitle: '',
        content: '',
        items: [],
        blocks: [body],
        kind: 'markdown'
      })
    }
  }

  return { sections: visibleSections, summary }
}
