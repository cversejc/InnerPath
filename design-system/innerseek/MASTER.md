# chenvis / 辰鉴 Design System

> This file records the visual system that the current implementation actually uses.
> The canonical global tokens live in `src/styles/foundation.css` and are assembled
> by `src/style.css`; page-level calendar and admin tokens are scoped extensions below.

---

**Project:** chenvis / 辰鉴

**Updated:** 2026-10-03

**Product type:** Personal insight, report and decision-calendar product
**Visual thesis:** A calm Chinese editorial interface built from paper, ink, cinnabar,
gold and jade. It should feel reflective and trustworthy, while remaining practical
enough for forms, calendars and operations work.

## Global rules

### Color palette

| Role | Value | CSS variable | Usage |
|------|-------|--------------|-------|
| Paper | `#f8f1e6` | `--paper` | Global page background |
| Paper soft | `#fffaf0` | `--paper-soft` | Card and input surfaces |
| Paper deep | `#ead9bf` | `--paper-deep` | Warm depth and gradients |
| Ink | `#2f241b` | `--ink` | Headings and primary text |
| Ink soft | `#614d3d` | `--ink-soft` | Secondary copy |
| Muted | `#7d6653` | `--muted` | Supporting text; use sparingly for small type |
| Cinnabar | `#b5574c` | `--cinnabar` | Brand accent, focus and decorative emphasis; passes 4.5:1 on paper |
| Cinnabar deep | `#9e3f35` | `--cinnabar-deep` | Primary actions, links and error text |
| Gold | `#d9ba62` | `--gold` | Highlight, seal and editorial ornament |
| Gold deep | `#8b5a14` | `--gold-deep` | Small labels and secondary emphasis |
| Jade | `#6f9f93` | `--jade` | Positive, steady and reflective states |
| Line | `rgba(139, 90, 20, 0.16)` | `--line` | Borders and dividers |
| Surface | `rgba(255, 250, 240, 0.78)` | `--surface` | Translucent panels |
| Strong surface | `rgba(255, 252, 245, 0.94)` | `--surface-strong` | High-contrast cards and overlays |

Calendar-specific semantic tones are scoped to `.calendar-page`:

| Meaning | Value |
|---------|-------|
| Calendar ink | `#2e251d` |
| Calendar muted | `var(--muted)` → `#7d6653` |
| 推进 / positive | `#658f73` |
| 观察 / neutral | `#bd9550` |
| 收气 / caution | `#b45d58` |

Contrast rule: normal reading text should target at least 4.5:1. Do not use muted
colors for long-form copy or critical labels without checking the actual background.

### Typography

- **Display:** `"Source Han Serif SC", "Noto Serif SC", "Songti SC", STSong, SimSun, serif`
- **Body / interface:** `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif`
- **Technical:** `ui-monospace, "SFMono-Regular", "SF Mono", Consolas, "Liberation Mono", Menlo, monospace`
- The web bundle loads only the Source Han Serif SC display cuts. Body and interface text
  use the platform's system UI font stack; no external Google Fonts import is used.
- Display roles cover the logo fallback, hero, page H1/H2, report H1/H2 and key insights.
  Card titles, H3/H6, navigation, buttons, forms, tables and AI dialogue stay in the UI
  stack. Prompt, DSL, JSON, IDs and debug output use the technical stack.
- Body text defaults to `16px` with `line-height: 1.6`; report prose uses `1.75`.
- Display weights are `400 / 500 / 600`; UI weights are `400 / 500 / 600`. The project
  avoids 700+ weights and browser-synthesized bold.
- The canonical font, size, leading and weight tokens live in `src/styles/foundation.css`.
  Reuse them instead of introducing page-level font families or one-off scales.
- Mobile form controls remain at least `16px` to prevent browser zoom.
- English kickers and metadata may be smaller, but user-facing explanatory copy should
  normally remain at `13px` or larger.

### Typography maintenance

- Treat this section and the tokens in `src/styles/foundation.css` as the single source
  of truth for new frontend features. Start with a semantic role and shared token before
  introducing a local font, size, line-height or weight.
- Keep `src/styles/vant.css` aligned when a typography token affects Vant controls. Do not
  add external font loading or a second font family system in a page or feature stylesheet.
- When the approved typography changes, update the implementation tokens, Vant mapping
  when applicable, and this document in the same change. Record the source design
  decision and verify with `npm run build` plus `git diff --check`.

### Spacing and shape

| Token | Value |
|-------|-------|
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-5` | `24px` |
| `--space-6` | `32px` |
| `--space-7` | `48px` |
| `--radius-card` | `18px` |
| `--button-radius` | `13px` |
| `--button-height` | `46px` |
| `--touch-target` | `44px` minimum; prefer `48px` for primary mobile actions |

Use rounded paper cards with restrained depth. Avoid excessive pills: reserve pill
shapes for statuses, seals, tags and compact metadata.

### Motion and viewport behavior

- `--motion-fast: 150ms`
- `--motion-standard: 220ms`
- Use the shared ease-out curve for buttons, cards and panels.
- Respect `prefers-reduced-motion` and remove non-essential transitions.
- Desktop top navigation is `70px`; mobile top navigation is `62px` and the mobile
  bottom navigation is `64px` plus the safe-area inset.
- Support viewport checks at `320px`, `375px`, `768px`, `1024px` and `1440px`.

## Component conventions

### Mobile UI library

- Vant 4 is the shared library for mobile interaction primitives such as buttons, cells, tab bars, fields, pickers, popups and dialogs.
- Import only the components a view uses, with their component styles; do not globally register the full library.
- Vant theme variables are mapped to the project tokens in `src/styles/vant.css`. Do not set one-off palette values in individual pages.
- Use Vant `Field` for reusable text entry and Vant `Button` for common form actions; retain native date and select controls when their platform picker behavior is the better fit.
- Branded choice cards may use Vant `Button` with `aria-pressed`; keep their card composition and selected-state styling in project CSS.
- Keep brand-specific compositions such as navigation, profile summaries and report sections in project-owned components; use Vant for their common interactive controls.

### Buttons

- Primary: cinnabar gradient, light paper text, strong but soft shadow.
- Secondary: light paper surface, warm border, deep cinnabar text.
- Both use a stable `46px` minimum height, `13px` radius and `8px` icon gap.
- Every button needs visible hover, focus, pressed and disabled states.
- Loading labels must not cause the button to change size.

### Cards and panels

- Use `paper-card` for user-facing editorial surfaces.
- Use translucent `surface`/`surface-strong` layers over the paper background.
- Admin panels may be denser, but must retain the same ink, border and status colors.

### Inputs and forms

- Visible labels are required; placeholders are supplementary only.
- Inputs use warm borders, `14px` radius and a cinnabar focus ring.
- Mobile input text stays at least `16px`.
- Inline errors sit close to the relevant field, use live-region semantics, and do not
  replace the user’s entered data.

### Navigation and overlays

- Mobile bottom navigation owns the four primary destinations: 首页、报告、日历、我的。
- Hamburger navigation is reserved for secondary links, role-specific entries and
  account actions.
- Menu, sheet, drawer and modal surfaces must provide dialog semantics, Escape close,
  focus entry, focus containment and focus restoration.
- Fixed navigation must be compensated by page padding and safe-area variables.

### Icons

- Use the shared `IconMark` SVG icon set for structural icons.
- Icons next to visible text are decorative (`aria-hidden`). Standalone icon controls
  must provide an accessible name on the control.
- Do not use Emoji as structural UI icons.

## Page patterns

- **Marketing / entry:** editorial hero, one clear primary CTA, supporting CTA only when
  it has a distinct next step.
- **Assessment:** progress indicator, one step at a time, field-level feedback and
  clear recovery on generation failure.
- **Calendar:** overview first, selected-day detail second, records alongside guidance;
  mobile detail opens as a sheet above the bottom navigation.
- **Reports:** content-first reading layout with a single next action into the decision
  calendar.
- **Admin:** scanable metrics, filters, tables or mobile cards, explicit loading/empty/
  error states and task-oriented drawers.
- **Consultant report workbench:** the report overview owns the six-stage rail.
  Selecting a node opens a viewport-height workspace with a compact client header,
  node selector and persistent function/tool controls. Only the active work content
  scrolls; navigation never overlays it. Long goals and responsibilities open in
  the task dialog. The node home gives the human task and dedicated work entries.
  Switching views resets the content scroll and reveals the selected navigation item.
  Profile and situation inputs use a labeled field grid for comparison at a glance.
  Collections open in a compact overview, with source-node filters and a detail reader;
  long analysis and report inputs also support complete continuous reading. Preserve
  the confirmed report order, complete text and source disclosures. Editing and review
  actions retain the single-record selector with previous/next actions.
  Stored calculations use four-pillar comparisons, count tables, a chronological
  dayun timeline and grouped palace records. Keep calculation assumptions visible,
  fold original JSON, and never turn occurrence counts into inferred strength scores.
  Wide prose tables scroll inside their own region on mobile. Quality dimension
  bars reflect the stored score and maximum without changing delivery thresholds.
  Skills and completion checklists open in dialogs rather than permanent side columns.
  Skill buttons invoke actual commands, show prerequisites, and keep history read-only.
  Report overview retains the delivered report entry. See
  `docs/consultant-analysis-implementation.md` for the decision and browser acceptance.
- **Skill and example workbench:** organize skills by the six consultant report nodes,
  using Chinese names and descriptions. A compact header, skill catalog and function
  navigation remain visible while only the active work content scrolls. On mobile,
  replace the catalog with a native skill selector. Use separate views for usage,
  examples, runs, maintenance, trial runs and evaluation; show only role-appropriate
  actions. Read examples and run output as labeled Chinese content, one selected
  record at a time. Fold stable technical keys and original JSON behind explicit
  disclosures. Common maintenance edits use labeled goal/method fields while
  preserving the complete configuration. Keep the originating consultant node
  and report in the return link. See `docs/consultant-analysis-implementation.md`.

## Anti-patterns

- Bright neon or unrelated pastel palettes
- Emoji used as structural icons
- Low-contrast muted copy or body text below `12px`
- Duplicate primary navigation patterns with no hierarchy
- Hover-only actions or cards that promise interaction without behavior
- Layout-shifting hover states
- Fixed overlays that hide content or keyboard focus
- Decorative density that competes with the report, form or operational task

## Source and maintenance

- Global source: `src/style.css`
- Shared navigation: `src/components/BrandNav.vue`
- Shared icons: `src/components/IconMark.vue`
- Page-specific tokens must be added as documented scoped extensions, not silently
  introduced as unrelated one-off colors.
- When changing the visual direction, update this file and the implementation together.
