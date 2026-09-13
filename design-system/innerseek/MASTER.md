# Innerseek / 辰鉴 Design System

> This file records the visual system that the current implementation actually uses.
> The canonical global tokens live in `src/style.css`; page-level calendar and admin
> tokens are documented as scoped extensions below.

---

**Project:** Innerseek / 辰鉴

**Updated:** 2026-09-13

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

- **Display:** `"Noto Serif SC", "Songti SC", STSong, SimSun, serif`
- **Interface:** `"Avenir Next", "Manrope", "PingFang SC", "Microsoft YaHei", sans-serif`
- Fonts are resolved locally/system-first. No external Google Fonts import is part of
  the current implementation.
- Body text defaults to `16px` with `line-height: 1.6`.
- Mobile form controls remain at least `16px` to prevent browser zoom.
- English kickers and metadata may be smaller, but user-facing explanatory copy should
  normally remain at `13px` or larger.

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
