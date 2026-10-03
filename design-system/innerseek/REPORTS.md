# Personal Report Presentation

This document defines the reusable presentation rules for personal reports. Global
color, typography, spacing and interaction tokens remain governed by
[`MASTER.md`](./MASTER.md); the report implementation lives in
`src/features/reports/`.

## Reading Structure

Every report uses the same editorial shell and lets its content determine the body:

1. Cover with report title, recipient and brand.
2. A short shared foreword that frames the report as reference material, not a
   diagnosis or a fixed conclusion.
3. A contents page generated from the sections that have content.
4. One or more report sections generated from the supplied data.
5. A closing page only when the report contains a summary or message.

Do not add fixed chapter names, sample answers, invented advice, empty cards or
placeholder lists. Omit fields with no value. When no body content is available, show
one explicit empty state. Keep the report title and recipient visible on the cover;
running headers identify the current section on content pages.

## Content Contract

New report content should use `structured_sections` (or the equivalent camel-case
`structuredSections`) so each report can choose its own section count and wording. The
renderer accepts an object keyed by section ID or an ordered array of sections. A
section may provide `title`, `subtitle`, `content`, `items`, and nested `subsections`,
`sections`, or `children`. Content blocks may use `title`, `subtitle`, `content`,
`items`, and nested blocks. Plain strings and lists are also supported.

The current generator's `foundation`, `energy`, `topics`, and `summary` entries are
supported. `foundation.data` is rendered with the report's structured-data treatment;
topic entries become individual sections. Unknown section IDs remain renderable when
their values follow the same content-block shape.

Content source priority is:

1. Non-empty structured sections, with structured foundation data and summary.
2. Legacy Markdown when no usable structured sections are present.
3. Existing report fields (`energy_profile`, `relationship_pattern`,
   `career_guidance`, `personal_growth`) for reports without either source.

Do not render multiple sources for the same report. This prevents a full Markdown
report and its extracted fields from appearing twice. Empty arrays and blank strings
are omitted. Keep the original report wording; presentation code should not generate
personal advice or infer missing values.

Legacy Markdown supports headings, bold text, unordered lists and horizontal rules.
Escape raw HTML before formatting. Do not pass report text directly to `v-html` or
inject untrusted markup.

## Visual Hierarchy

- Use the existing paper, ink, gold and dark closing-page colors defined by
  `report-document.css`; use global design tokens for the surrounding application UI.
- Use `--font-display` for the cover and section headings, `--font-body` for report
  prose, and `--font-ui` for labels and metadata. Do not add page-level font imports,
  font families, unsupported weights or letter spacing.
- Keep prose comfortable to scan: body copy is at least `16px` on the web, uses the
  shared prose leading, and is split by meaningful headings and lists.
- Render nested blocks with consistent heading levels, restrained borders and paper
  surfaces. Use dark callouts only for short, high-value passages; do not turn every
  paragraph into a card.
- Use global typography tokens for prose, nested headings and metadata. The fixed A4
  composition may use report-scoped `--report-font-*` roles for the cover title,
  section titles, folio number and key data values; keep those roles inside the report
  stylesheet and document them here. Running heads and footers are metadata and may
  use the compact 10px report role.
- Use the same semantic structure in browser and PDF. The report title is the page
  `h1`; each major section is an `h2`; nested content uses `h3` and below.

## Responsive and Print Layout

- On desktop, present pages at the A4 proportion and cap their width at `210mm`.
- On narrow screens, let each page use the available width, reduce outer padding and
  stack multi-column data. Keep body text legible and prevent long names, headings,
  lists and values from overflowing.
- The contents page lists section order, not page numbers. Section length varies, so
  do not display a page number unless it is computed from the final rendered layout.
- Print with CSS paged media at A4 with backgrounds enabled. Start major sections on a
  new page where appropriate; let long sections continue naturally across pages.
  Avoid splitting short headings from their first paragraph and preserve widows and
  orphans for prose.
- The Playwright export must open the same report route and use the same Vue template
  and styles as web reading. Wait for the report-ready marker, fonts and images before
  calling `page.pdf()` with print media, A4 sizing, backgrounds and CSS page-size
  preference enabled. Hide application navigation and export controls in print.

## Review Checklist

- The contents reflect the actual sections and order for this report.
- Missing foundation data or summary removes those parts without leaving blank pages.
- Short and long sections both retain heading hierarchy and readable spacing.
- Markdown is escaped, and structured text is rendered as text rather than markup.
- Desktop, mobile and A4 PDF use the same content and visual hierarchy.
