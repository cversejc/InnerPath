# Repository Instructions

## Architecture and Development Conventions

- Read [一期模块边界与开发约定](docs/architecture/一期模块边界与开发约定.md) before adding or moving application code. It is the source of truth for domain ownership, dependency direction, API boundaries, shared implementations, and test commands.
- Keep backend dependencies flowing from HTTP/task adapters through application orchestration into domain modules. Domain modules must not depend on API routes, application orchestration, or task entry points.
- Put frontend API calls in the owning `src/features/<domain>/api.js` and send them through `src/utils/apiClient.js`. Keep cross-domain components in `src/components/`; keep domain-only components inside their feature.
- Use Vue 3 and Vant 4 for the established frontend stack. Reuse existing shared components and controls before adding another implementation or UI library. Follow [the design system](design-system/innerseek/MASTER.md) for visual tokens and conventions.
- Keep files focused on one workflow or responsibility. Around 400 lines is a point to review natural split boundaries, not a target that justifies fragmenting cohesive code.

## GitHub Remote

- Use the SSH remote for GitHub operations: `git@github.com:cversejc/InnerPath.git`
- Check the configured remote before fetching or pushing with `git remote -v`
- Verify SSH access with `ssh -T -o BatchMode=yes git@github.com`. A successful authentication prints a GitHub authentication message and exits with code 1 because GitHub does not provide shell access
- Push the current branch with `git push origin <branch>` after confirming the worktree is clean
- If `origin` points to an HTTPS URL or GitHub port 443 is unreachable, switch it with `git remote set-url origin git@github.com:cversejc/InnerPath.git` and retry over SSH
- Never put access tokens, passwords, or private keys in repository files or remote URLs
