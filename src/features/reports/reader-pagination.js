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

  for (const line of markdown.split('\n')) {
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

  if (block.type === 'heading-content') {
    const headingEnd = block.text.indexOf('\n\n')
    if (headingEnd >= 0) {
      const heading = block.text.slice(0, headingEnd)
      const body = block.text.slice(headingEnd + 2)
      const bodyLimit = Math.max(1, limit - characterLength(heading) - 2)
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
