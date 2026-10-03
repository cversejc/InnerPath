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

  const flushParagraph = () => {
    if (!paragraph.length) return
    blocks.push(`<p>${paragraph.map(formatInline).join('<br>')}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!list.length) return
    blocks.push(`<ul>${list.map(item => `<li>${formatInline(item)}</li>`).join('')}</ul>`)
    list = []
  }

  for (const line of content.replace(/\r\n?/g, '\n').split('\n')) {
    const heading = line.match(/^(#{1,5})\s+(.+)$/)
    const item = line.match(/^\s*[-*]\s+(.+)$/)

    if (heading) {
      flushParagraph()
      flushList()
      const level = Math.min(heading[1].length + 1, 6)
      blocks.push(`<h${level}>${formatInline(heading[2])}</h${level}>`)
    } else if (item) {
      flushParagraph()
      list.push(item[1])
    } else if (/^\s*---\s*$/.test(line)) {
      flushParagraph()
      flushList()
      blocks.push('<hr>')
    } else if (!line.trim()) {
      flushParagraph()
      flushList()
    } else {
      flushList()
      paragraph.push(line)
    }
  }

  flushParagraph()
  flushList()
  return blocks.join('')
}
