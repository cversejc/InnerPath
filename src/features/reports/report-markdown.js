export function formatReportMarkdown(content) {
  if (!content) return ''

  const escapeHtml = value => value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
  const formatInline = value => escapeHtml(value).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  const blocks = []
  let paragraph = []
  let list = []
  let listType = 'ul'
  let quote = []

  const flowMarkup = value => {
    const pieces = value.trim().split(/\s*(→|->|➜|⟶|↓)\s*/)
    const nodes = pieces.filter((_, index) => index % 2 === 0)
    const separators = pieces.filter((_, index) => index % 2 === 1)
    if (nodes.length < 2 || nodes.length > 7 || nodes.some(node => Array.from(node.trim()).length > 36)) return ''
    const content = nodes.map((node, index) => `${index ? `<span class="report-flow__arrow" aria-hidden="true">${separators[index - 1]}</span>` : ''}<span class="report-flow__node">${formatInline(node.trim())}</span>`).join('')
    return `<div class="report-inline-flow" role="list" aria-label="过程顺序">${content}</div>`
  }

  const flushParagraph = () => {
    if (!paragraph.length) return
    const value = paragraph.join('\n')
    const normalized = value.trim()
    const flow = paragraph.length === 1 ? flowMarkup(normalized) : ''
    const takeaway = normalized.match(/^\*\*(结论|核心结论|关键发现|重要提醒)\*\*[：:]\s*([\s\S]+)$/)
    if (flow) blocks.push(flow)
    else if (takeaway) blocks.push(`<aside class="report-inline-takeaway"><span>${formatInline(takeaway[1])}</span><p>${formatInline(takeaway[2]).replace(/\n/g, '<br>')}</p></aside>`)
    else blocks.push(`<p>${paragraph.map(formatInline).join('<br>')}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!list.length) return
    blocks.push(`<${listType}${listType === 'ul' && list.some(item => item.checked !== null) ? ' class="report-checklist"' : ''}>${list.map(item => {
      const marker = item.checked === null ? '' : `<span class="report-checklist__mark" aria-hidden="true">${item.checked ? '✓' : ''}</span>`
      return `<li>${marker}${formatInline(item.text)}</li>`
    }).join('')}</${listType}>`)
    list = []
    listType = 'ul'
  }
  const flushQuote = () => {
    if (!quote.length) return
    blocks.push(`<blockquote>${quote.map(line => `<p>${formatInline(line)}</p>`).join('')}</blockquote>`)
    quote = []
  }

  for (const line of content.replace(/\r\n?/g, '\n').split('\n')) {
    const heading = line.match(/^(#{1,5})\s+(.+)$/)
    const item = line.match(/^\s*(?:(\d+)[.)、]|[-*+])\s+(.+)$/)
    const quoted = line.match(/^\s*>\s?(.*)$/)

    if (heading) {
      flushParagraph()
      flushList()
      flushQuote()
      const level = Math.min(heading[1].length + 2, 5)
      blocks.push(`<h${level}>${formatInline(heading[2])}</h${level}>`)
    } else if (quoted) {
      flushParagraph()
      flushList()
      quote.push(quoted[1])
    } else if (item) {
      flushParagraph()
      flushQuote()
      const nextType = item[1] ? 'ol' : 'ul'
      if (list.length && listType !== nextType) flushList()
      listType = nextType
      const task = item[2].match(/^\[([ xX])\]\s*(.*)$/)
      list.push(task
        ? { text: task[2], checked: task[1].toLowerCase() === 'x' }
        : { text: item[2], checked: null })
    } else if (/^\s*---\s*$/.test(line)) {
      flushParagraph()
      flushList()
      flushQuote()
      blocks.push('<hr>')
    } else if (!line.trim()) {
      flushParagraph()
      flushList()
      flushQuote()
    } else {
      flushList()
      flushQuote()
      paragraph.push(line)
    }
  }

  flushParagraph()
  flushList()
  flushQuote()
  return blocks.join('')
}
