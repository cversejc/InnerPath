const DEFAULT_PAGE_CHARACTER_LIMIT = 600

function characterLength(value) {
  return Array.from(value).length
}

function splitLineAtSentences(line, limit) {
  if (characterLength(line) <= limit) return [line]

  const sentences = line.match(/[^。！？!?；;]+[。！？!?；;]?/gu) || [line]
  const chunks = []
  let current = ''

  for (const sentence of sentences) {
    if (characterLength(sentence) > limit) {
      if (current) chunks.push(current)
      current = ''
      const characters = Array.from(sentence)
      for (let index = 0; index < characters.length; index += limit) {
        const chunk = characters.slice(index, index + limit).join('')
        if (characterLength(chunk) === limit) chunks.push(chunk)
        else current = chunk
      }
      continue
    }

    if (current && characterLength(current) + characterLength(sentence) > limit) {
      chunks.push(current)
      current = sentence
    } else {
      current += sentence
    }
  }

  if (current) chunks.push(current)
  return chunks
}

function splitLongText(value, limit) {
  const chunks = []
  let current = ''

  for (const line of value.split('\n')) {
    for (const lineChunk of splitLineAtSentences(line, limit)) {
      const separator = current ? '\n' : ''
      if (current && characterLength(current) + separator.length + characterLength(lineChunk) > limit) {
        chunks.push(current)
        current = lineChunk
      } else {
        current += `${separator}${lineChunk}`
      }
    }
  }

  if (current) chunks.push(current)
  return chunks
}

function isStandaloneSectionLabel(line) {
  const text = line.trim().replace(/^\*\*(.+)\*\*$/, '$1').replace(/^__(.+)__$/, '$1').trim()
  if (!text || characterLength(text) > 48 || /[。！？!?；;]$/.test(text)) return false
  return /^(?:[①-⑳]|\d+(?:\.\d+)*[、.)）])/.test(text) || /[：:]$/.test(text)
}

function splitMarkdownTableCells(line) {
  const source = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  const cells = []
  let cell = ''
  for (let index = 0; index < source.length; index += 1) {
    if (source[index] === '\\' && source[index + 1] === '|') {
      cell += '|'
      index += 1
    } else if (source[index] === '|') {
      cells.push(cell.trim())
      cell = ''
    } else {
      cell += source[index]
    }
  }
  cells.push(cell.trim())
  return cells
}

function isMarkdownTableDelimiter(line) {
  return Boolean(line?.includes('|'))
    && splitMarkdownTableCells(line).every(cell => /^:?-{3,}:?$/.test(cell))
}

function isMarkdownTableStart(lines, index) {
  return Boolean(lines[index]?.includes('|')) && isMarkdownTableDelimiter(lines[index + 1])
}

function splitMarkdownTable(markdown, limit) {
  const lines = markdown.split('\n')
  if (!isMarkdownTableStart(lines, 0)) return null

  const header = lines.slice(0, 2)
  const rows = lines.slice(2)
  if (!rows.length) return [markdown]

  const headerLength = characterLength(header.join('\n'))
  const pages = []
  let pageRows = []
  let pageLength = headerLength
  const flushRows = () => {
    if (!pageRows.length) return
    pages.push([...header, ...pageRows].join('\n'))
    pageRows = []
    pageLength = headerLength
  }

  for (const row of rows) {
    const rowLength = characterLength(row) + 1
    if (pageRows.length && pageLength + rowLength > limit) flushRows()
    pageRows.push(row)
    pageLength += rowLength
  }
  flushRows()
  return pages
}

function parseMarkdownBlocks(markdown) {
  const blocks = []
  let pendingHeadings = []
  let paragraphLines = []
  let listLines = []

  const emit = (text, type) => {
    if (!text) return
    const headingPrefix = pendingHeadings.length ? `${pendingHeadings.join('\n')}\n\n` : ''
    blocks.push({
      text: `${headingPrefix}${text}`,
      type: headingPrefix ? 'heading-content' : type
    })
    pendingHeadings = []
  }
  const flushHeadings = () => {
    if (!pendingHeadings.length) return
    blocks.push({ text: pendingHeadings.join('\n'), type: 'heading' })
    pendingHeadings = []
  }
  const flushParagraph = () => {
    if (!paragraphLines.length) return
    emit(paragraphLines.join('\n'), 'paragraph')
    paragraphLines = []
  }
  const flushList = () => {
    if (!listLines.length) return
    emit(listLines.join('\n'), 'list')
    listLines = []
  }

  const lines = markdown.split('\n')
  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex]
    if (isMarkdownTableStart(lines, lineIndex)) {
      flushParagraph()
      flushList()
      const tableLines = [line, lines[lineIndex + 1]]
      lineIndex += 2
      while (lineIndex < lines.length && lines[lineIndex].includes('|') && !isMarkdownTableDelimiter(lines[lineIndex])) {
        tableLines.push(lines[lineIndex])
        lineIndex += 1
      }
      lineIndex -= 1
      emit(tableLines.join('\n'), 'table')
      continue
    }
    const heading = /^#{1,5}\s+/.test(line)
    const listItem = /^\s*[-*]\s+/.test(line)
    const horizontalRule = /^\s*---\s*$/.test(line)
    const sectionLabel = !heading && !listItem && !horizontalRule && isStandaloneSectionLabel(line)

    if (!line.trim()) {
      flushParagraph()
      flushList()
    } else if (heading || sectionLabel) {
      flushParagraph()
      flushList()
      pendingHeadings.push(line)
    } else if (horizontalRule) {
      flushParagraph()
      flushList()
      emit(line, 'rule')
    } else if (listItem) {
      flushParagraph()
      listLines.push(line)
    } else {
      flushList()
      paragraphLines.push(line)
    }
  }

  flushParagraph()
  flushList()
  flushHeadings()
  return blocks
}

function splitMarkdownBlock(block, limit) {
  if (characterLength(block.text) <= limit) return [block]

  if (block.type === 'table') {
    const tablePages = splitMarkdownTable(block.text, limit)
    if (tablePages) return tablePages.map(text => ({ text, type: 'table' }))
  }

  if (block.type === 'heading-content') {
    const headingEnd = block.text.indexOf('\n\n')
    if (headingEnd >= 0) {
      const heading = block.text.slice(0, headingEnd)
      const body = block.text.slice(headingEnd + 2)
      const bodyLimit = Math.max(1, limit - characterLength(heading) - 2)
      const tablePages = splitMarkdownTable(body, bodyLimit)
      if (tablePages) {
        return tablePages.map((content, index) => ({
          text: index === 0 ? `${heading}\n\n${content}` : content,
          type: index === 0 ? 'heading-content' : 'table'
        }))
      }
      return splitLongText(body, bodyLimit).map((content, index) => ({
        text: index === 0 ? `${heading}\n\n${content}` : content,
        type: index === 0 ? 'heading-content' : block.type
      }))
    }
  }

  return splitLongText(block.text, limit).map(text => ({ text, type: block.type }))
}

/** Split long legacy Markdown into A4-sized reader fragments without dropping wording. */
export function paginateMarkdownForReader(markdown, maxCharacters = DEFAULT_PAGE_CHARACTER_LIMIT) {
  const source = String(markdown || '').replace(/\r\n?/g, '\n').trim()
  if (!source) return []

  const limit = Math.max(1, Math.floor(Number(maxCharacters) || DEFAULT_PAGE_CHARACTER_LIMIT))
  const blocks = parseMarkdownBlocks(source).flatMap(block => splitMarkdownBlock(block, limit))
  const pages = []
  let current = ''
  let previousType = ''

  for (const block of blocks) {
    const separator = !current ? '' : previousType === 'list' && block.type === 'list' ? '\n' : '\n\n'
    if (current && characterLength(current) + separator.length + characterLength(block.text) > limit) {
      pages.push(current)
      current = block.text
    } else {
      current += `${separator}${block.text}`
    }
    previousType = block.type
  }

  if (current) pages.push(current)
  return pages
}

function plainCharacterLength(value) {
  return characterLength(String(value || '').replace(/[#>*_`~-]/g, ''))
}

function fragmentSize(block) {
  return Math.max(1, plainCharacterLength(block.title)
    + plainCharacterLength(block.subtitle)
    + plainCharacterLength(block.content)
    + (block.items || []).reduce((total, item) => total + plainCharacterLength(item), 0)
    + plainCharacterLength(block.comparison?.from)
    + plainCharacterLength(block.comparison?.to)
    + (block.metadata || []).reduce((total, item) => total + plainCharacterLength(item.value), 0)
    + (block.title ? 18 : 0))
}

function splitBlockContent(block, depth, limit) {
  const titleCost = plainCharacterLength(block.title) + plainCharacterLength(block.subtitle)
    + (block.title ? 18 : 0)
    + (block.metadata || []).reduce((total, item) => total + plainCharacterLength(item.value), 0)
  const contentLimit = Math.max(1, limit - titleCost)
  const contentParts = block.content
    ? paginateMarkdownForReader(block.content, contentLimit)
    : []
  const fragments = contentParts.map((content, index) => ({
    ...block,
    depth,
    content,
    items: [],
    continued: index > 0,
    children: []
  }))

  if (block.comparison && !block.content && !block.items?.length) {
    const fromParts = paginateMarkdownForReader(block.comparison.from || '', contentLimit)
    const toParts = paginateMarkdownForReader(block.comparison.to || '', contentLimit)
    const partCount = Math.max(fromParts.length, toParts.length, 1)
    for (let index = 0; index < partCount; index += 1) {
      fragments.push({
        ...block,
        title: index ? '' : block.title,
        subtitle: index ? '' : block.subtitle,
        comparison: {
          ...block.comparison,
          from: fromParts[index] || (fromParts.length === 1 ? fromParts[0] : ''),
          to: toParts[index] || (toParts.length === 1 ? toParts[0] : '')
        },
        depth,
        content: '',
        items: [],
        continued: index > 0,
        children: []
      })
    }
  }

  if (block.items?.length) {
    let items = []
    let itemsLength = 0
    const flushItems = () => {
      if (!items.length) return
      fragments.push({
        ...block,
        title: fragments.length ? '' : block.title,
        subtitle: '',
        content: '',
        items,
        depth,
        continued: fragments.length > 0,
        children: []
      })
      items = []
      itemsLength = 0
    }
    for (const item of block.items) {
      const chunks = characterLength(String(item)) > contentLimit
        ? paginateMarkdownForReader(String(item), contentLimit)
        : [String(item)]
      for (const chunk of chunks) {
        const itemLength = plainCharacterLength(chunk)
        if (items.length && itemsLength + itemLength > contentLimit) flushItems()
        items.push(chunk)
        itemsLength += itemLength
      }
    }
    flushItems()
  }

  if (!fragments.length && block.title) {
    fragments.push({ ...block, depth, content: '', items: [], children: [] })
  }
  return fragments
}

function flattenReportBlocks(blocks, limit, depth = 0) {
  return (blocks || []).flatMap(block => {
    if (!block || typeof block !== 'object') return []
    const blockDepth = Number.isInteger(block.depth) ? block.depth : depth
    const ownFragments = splitBlockContent(block, blockDepth, limit)
    return [...ownFragments, ...flattenReportBlocks(block.children, limit, blockDepth + 1)]
  })
}

function safeAnchorPart(value) {
  return String(value || 'block').replace(/[^a-z\d_-]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'block'
}

/** Paginate a normalized section while retaining a flat, depth-aware block list per page. */
export function paginateReportSection(section, maxCharacters = DEFAULT_PAGE_CHARACTER_LIMIT) {
  const limit = Math.max(1, Math.floor(Number(maxCharacters) || DEFAULT_PAGE_CHARACTER_LIMIT))
  const rootBlocks = [...(section.blocks || [])]
  if (section.content || section.items?.length || section.comparison || section.metadata?.length) {
    rootBlocks.unshift({
      id: `${section.id}-lead`,
      title: '',
      subtitle: '',
      content: section.content || '',
      items: section.items || [],
      children: [],
      depth: 0,
      displayType: section.displayType || (section.items?.length ? 'list' : 'prose'),
      comparison: section.comparison || null,
      metadata: section.metadata || []
    })
  }

  const fragments = flattenReportBlocks(rootBlocks, limit)
  if (!fragments.length) return [{ content: '', blocks: [] }]

  const pages = []
  let current = []
  let currentLength = 0
  const pushPage = () => {
    if (!current.length) return
    pages.push({ content: '', blocks: current })
    current = []
    currentLength = 0
  }

  fragments.forEach((fragment, index) => {
    const size = fragmentSize(fragment)
    const isHeadingOnly = Boolean(fragment.title && !fragment.content && !fragment.items?.length && !fragment.comparison && !fragment.metadata?.length)
    const nextSize = isHeadingOnly && fragments[index + 1] ? fragmentSize(fragments[index + 1]) : 0
    if (current.length && currentLength + size + nextSize > limit) pushPage()
    if (current.length && currentLength + size > limit) pushPage()
    current.push(fragment)
    currentLength += size
  })
  pushPage()

  const fragmentCounts = new Map()
  pages.forEach((page, pageIndex) => {
    page.blocks = page.blocks.map(block => {
      const fragmentIndex = fragmentCounts.get(block.id) || 0
      fragmentCounts.set(block.id, fragmentIndex + 1)
      return {
        ...block,
        anchorId: `report-${safeAnchorPart(section.id)}-${safeAnchorPart(block.id)}-${fragmentIndex + 1}`,
        fragmentIndex
      }
    })
    page.pageInSection = pageIndex
  })
  return pages
}
