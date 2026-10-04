# chenvis / 辰鉴 Design System

> This file records the visual system that the current implementation actually uses.
> The canonical global tokens live in `src/styles/foundation.css` and are assembled
> by `src/style.css`; page-level calendar and admin tokens are scoped extensions below.

---

**Project:** chenvis / 辰鉴

**Updated:** 2026-10-04

**Product type:** Personal insight, report and decision-calendar product
**Visual thesis:** A calm Chinese editorial interface built from paper, ink, cinnabar,
gold and jade. It should feel reflective and trustworthy, while remaining practical
enough for forms, calendars and operations work.

## Global rules

### Color palette

| Role | Value | CSS variable | Usage |
|------|-------|--------------|-------|
| Paper | `#f7f4ed` | `--paper` | Global page background |
| Paper soft | `#fffcf6` | `--paper-soft` | Card and input surfaces |
| Paper deep | `#e9dfcf` | `--paper-deep` | Warm depth and gradients |
| Ink | `#302c25` | `--ink` | Headings and primary text |
| Ink soft | `#5f564b` | `--ink-soft` | Secondary copy |
| Muted | `#786b5c` | `--muted` | Supporting text; use sparingly for small type |
| Cinnabar | `#b5574c` | `--cinnabar` | Brand accent, focus and decorative emphasis; passes 4.5:1 on paper |
| Cinnabar deep | `#9e3f35` | `--cinnabar-deep` | Primary actions, links and error text |
| Gold | `#d9ba62` | `--gold` | Highlight, seal and editorial ornament |
| Gold deep | `#8b5a14` | `--gold-deep` | Small labels and secondary emphasis |
| Jade | `#6f9f93` | `--jade` | Positive, steady and reflective states |
| Line | `rgba(111, 88, 55, 0.14)` | `--line` | Borders and dividers |
| Surface | `rgba(255, 252, 246, 0.8)` | `--surface` | Translucent panels |
| Strong surface | `#fffcf6` | `--surface-strong` | High-contrast cards and overlays |

Calendar-specific semantic tones are scoped to `.calendar-page`:

| Meaning | Value |
|---------|-------|
| Calendar ink | `var(--ink)` → `#302c25` |
| Calendar muted | `var(--muted)` → `#786b5c` |
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
| `--button-radius` | `12px` |
| `--button-height` | `48px` |
| `--touch-target` | `44px` minimum; prefer `48px` for primary mobile actions |

Use rounded paper cards with restrained depth. Default cards use an opaque paper surface; reserve translucency for navigation and overlays. Avoid excessive pills: reserve pill
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

- Primary: cinnabar gradient, light paper text, restrained warm shadow.
- Secondary: light paper surface, warm border, deep cinnabar text.
- Both use a stable `48px` minimum height, `12px` radius and `8px` icon gap.
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

## Visual refinement decision · 2026-10-04

Source: the product-wide UI refinement requested on 2026-10-04; this section is the
maintained decision record for the implementation in this change.

- Retain the paper / ink / cinnabar / gold / jade identity. Lighten the paper and
  neutralize reading text to reduce the brown cast. Keep the existing locally
  bundled display fonts and UI font roles.
- Remove the full-page grid and large background illustration from content areas.
  Reuse the existing `src/assets/home-hero.webp` only for the home hero and desktop
  authentication brand panel; text sits on a light veil for contrast.
- Introduce `--line-strong` for inputs and selected surfaces, `--accent-soft` for
  subtle selection, and `--jade-deep: #356b59` for readable success text.
- Use `--content-width: 1120px`, `--page-gutter: 32px` (16px on mobile) and
  `--space-8: 64px` for consistent page rhythm. Operations tables may retain their
  wider containers. Cards use `--shadow-card`; prominent form panels use
  `--shadow-soft`. Avoid blur on repeated cards.
- Primary user actions and Vant buttons use the shared 16px body scale and 48px
  height; dense table commands may retain their documented compact styles.
  Vant fields use the shared 16px input scale. Bottom navigation labels use the
  12px caption token, with a subtle active icon background.
- Desktop navigation uses soft rectangular active states with a small underline;
  rounded pills remain reserved for metadata and status. Personal-space navigation
  uses the same restrained selection treatment.
- Home exposes exploration in the first viewport and links both product paths.
  Authentication uses an editorial brand panel and focused form on desktop, and a
  single-column form on mobile. Reports retain generous reading space; operation
  metrics use four desktop columns to match the four actual indicators. Mobile
  operation navigation wraps so every section remains visible. Calendar detail
  headers reserve room for the close control; status labels use readable deep tones.
- Verify narrow forms, fixed navigation and page overflow at 320 / 375 / 768 /
  1024 / 1440px, including authentication modes, assessment, calendar, reports,
  personal space and operations. Use local fixture data when no backend is running.
