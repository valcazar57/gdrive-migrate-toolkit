# Security & privacy

This toolkit touches your company's Google Drive. The biggest risks are **leaking
credentials** and **committing real data**. Read this before you run or publish
anything.

## Never commit these

- **`rclone.conf`** — it contains your OAuth tokens (full Drive access). This is the
  single most sensitive file. Find its path with `rclone config file`. It is in
  [`.gitignore`](.gitignore); keep it there.
- **Any log or CSV with real data**: `changes_*.csv`, `changes_evacuation_*.csv`,
  `*.log`, `*.tsv`, inventory dumps, `natives_*.csv`, listings.
- **Business documents**: session notes, plans, decisions, `README — STATE ...`,
  your real `AGENTS.md`/`CLAUDE.md`.
- **Real identifiers**: account names/emails, remote names, brands, domains, people,
  clients, fiscal entities, Drive folder IDs and share-URLs, absolute paths
  containing your Windows username.
- **The local mirror** (`D:/MIRROR`, `mirror/`, `data/`) — it's your actual data.

The committed repo must contain **method + generic scripts + empty templates only**.

## Before the first push

1. Confirm `.gitignore` covers `rclone.conf`, `*.log`, `*.tsv`, real `*.csv`,
   `data/`, `mirror/`, `.env`.
2. Grep the whole tree for forbidden terms (your real account/remote names, brands,
   clients, people, domains, emails, Windows username, Drive IDs) → must be **zero**.
3. Create the repo **private first**, review, then flip to public.

## Credential hygiene

- Use `scope=drive.readonly` for inventory/mirror-only work; full `scope=drive` only
  when you need server-side copy / purge.
- Revoke a remote's access at <https://myaccount.google.com/permissions> if a token
  may have leaked, and re-run `rclone config`.
- Never paste `rclone.conf` contents, tokens, or share-URLs into issues, PRs, chat
  logs or screenshots.

## Operational safety (data loss, not secrets)

- Scripts are **dry-run by default**; `--apply` is required to change anything.
- Always mirror to disk and verify counts/hashes **before** deleting a source.
- Deletion is to **trash** (`--drive-use-trash=true`), recoverable for 30 days — but
  the trash is a net, not a backup.

## Reporting a vulnerability

Open a GitHub issue for non-sensitive bugs. For anything involving credentials or a
potential data-loss bug, contact the maintainers privately (e.g. via the repo's
security advisory feature) rather than filing a public issue with details.
