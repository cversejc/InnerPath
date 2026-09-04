# Mobile Frontend Redesign Implementation Plan

> **For AI agents:** Execute this plan inline. Keep changes focused, run `npm run build`, then verify the mobile viewport visually.

**Goal:** Redesign the frontend with a mobile-first visual language inspired by the provided Compass AI reference site.

**Architecture:** Add a shared visual system in global CSS, then replace duplicated page-level visual structure on the primary user journey pages. Preserve existing Vue methods and route paths.

**Tech Stack:** Vue 3, Vue Router, Vite, scoped SFC styles, plain CSS.

---

### Task 1: Global Visual System

**Files:**
- Modify: `index.html`
- Modify: `src/style.css`

- [x] Set mobile-safe viewport and theme color in `index.html`.
- [x] Add CSS variables for paper background, cinnabar, gold, ink, muted text, surfaces, borders, and shadows.
- [x] Add reusable classes for mobile shell, navigation, hero art, cards, buttons, form controls, service lists, and footer.
- [x] Keep base styles accessible and avoid external UI libraries.

Verification: `npm run build` must complete after all tasks.

### Task 2: Home and Services

**Files:**
- Modify: `src/views/Home.vue`
- Modify: `src/views/Services.vue`

- [x] Rebuild `Home` as a mobile-first landing flow with layered landscape-style art, a compass-like hero panel, narrative sections, and service cards.
- [x] Rebuild `Services` as a mobile-first service catalogue with scan-friendly cards and clear CTAs.
- [x] Preserve existing route navigation methods.

Verification: `/pages/home/home` and `/pages/services/services` render at 390px width without horizontal overflow.

### Task 3: Assessment and Booking

**Files:**
- Modify: `src/views/Assessment.vue`
- Modify: `src/views/Booking.vue`

- [x] Replace visual markup where needed while preserving data fields and submit methods.
- [x] Make the assessment progress indicator compact and usable on mobile.
- [x] Make selection cards, date fields, topic cards, and booking form controls use the shared paper-card system.

Verification: `/pages/assessment/assessment` and `/pages/booking/booking` render at 390px width without horizontal overflow.

### Task 4: Final Verification

- [x] Run `npm run build`.
- [x] Start a local Vite server.
- [x] Inspect mobile and desktop viewports with browser automation or screenshots.
- [x] Fix any obvious layout overflow, illegible text, or broken interaction.
