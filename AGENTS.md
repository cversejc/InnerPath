# Repository Instructions

## Architecture and Development Conventions

- Read [一期模块边界与开发约定](docs/architecture/一期模块边界与开发约定.md) before adding or moving application code. It is the source of truth for domain ownership, dependency direction, API boundaries, shared implementations, and test commands.
- Keep backend dependencies flowing from HTTP/task adapters through application orchestration into domain modules. Domain modules must not depend on API routes, application orchestration, or task entry points.
- Put frontend API calls in the owning `src/features/<domain>/api.js` and send them through `src/utils/apiClient.js`. Keep cross-domain components in `src/components/`; keep domain-only components inside their feature.
- Use Vue 3 and Vant 4 for the established frontend stack. Reuse existing shared components and controls before adding another implementation or UI library. Follow [the design system](design-system/innerseek/MASTER.md) for visual tokens and conventions.
- Keep files focused on one workflow or responsibility. Around 400 lines is a point to review natural split boundaries, not a target that justifies fragmenting cohesive code.

## Visual and Typography Governance

- Read [the design system](design-system/innerseek/MASTER.md) before adding or changing frontend UI. It is the maintained product-level visual contract; the canonical implementation tokens live in `src/styles/foundation.css`.
- Use `var(--font-display)` for brand/display headings, `var(--font-body)` or `var(--font-ui)` for body and interface text, and `var(--font-mono)` for code, IDs, JSON, prompts and debug output. Reuse the shared `--text-*`, `--leading-*` and `--weight-*` tokens before adding a local value.
- Do not add page-level font imports, external font loading, direct font-family declarations, or 700+ weights without updating the design system and documenting the exception in the same change. Do not bypass `src/styles/vant.css` for Vant typography.
- When the typography specification changes, update `src/styles/foundation.css`, `src/styles/vant.css` when applicable, and `design-system/innerseek/MASTER.md` together. Keep the source design document or decision reference linked in the change description.
- During review of a new feature, check that headings, body copy, controls and technical output use the correct role; mobile form text remains at least `16px`; and no new one-off font scale or weight is introduced without a documented reason.

## GitHub Remote

- Use the SSH remote for GitHub operations: `git@github.com:cversejc/InnerPath.git`
- Check the configured remote before fetching or pushing with `git remote -v`
- Verify SSH access with `ssh -T -o BatchMode=yes git@github.com`. A successful authentication prints a GitHub authentication message and exits with code 1 because GitHub does not provide shell access
- Push the current branch with `git push origin <branch>` after confirming the worktree is clean
- If `origin` points to an HTTPS URL or GitHub port 443 is unreachable, switch it with `git remote set-url origin git@github.com:cversejc/InnerPath.git` and retry over SSH
- Never put access tokens, passwords, or private keys in repository files or remote URLs
