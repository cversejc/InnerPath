# Repository Instructions

## GitHub Remote

- Use the SSH remote for GitHub operations: `git@github.com:cversejc/InnerPath.git`
- Check the configured remote before fetching or pushing with `git remote -v`
- Verify SSH access with `ssh -T -o BatchMode=yes git@github.com`. A successful authentication prints a GitHub authentication message and exits with code 1 because GitHub does not provide shell access
- Push the current branch with `git push origin <branch>` after confirming the worktree is clean
- If `origin` points to an HTTPS URL or GitHub port 443 is unreachable, switch it with `git remote set-url origin git@github.com:cversejc/InnerPath.git` and retry over SSH
- Never put access tokens, passwords, or private keys in repository files or remote URLs
