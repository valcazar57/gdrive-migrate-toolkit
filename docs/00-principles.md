# 00 — Principles

The seven rules that keep this safe. They never change, regardless of material
type or company area. Full rationale in [`PLAYBOOK.md`](../PLAYBOOK.md) §0.

1. **Read-only first.** Inventory and understand before touching anything.
2. **Copy, never move *from* Drive.** Moving a file out of a synced folder deletes
   it from the cloud. Always migrate with a copy; delete the source only after
   verification.
3. **Nothing is truly deleted (yet).** Disposable items go to a quarantine
   (`99_REVIEW`), not the trash. Permanent deletion is the final phase, with
   explicit per-batch confirmation.
4. **Everything logged and reversible.** Each operation appends a row to a CSV
   (`source;dest;action`). Reversal = inverse CSV. The scripts here do this.
5. **Small batches.** dry-run → collision check → approval → execute → verify
   counts → next block.
6. **Confidentiality.** Minimize reading file contents. Don't upload anything to
   external services. Flag `LEGAL_REVIEW` for contracts, GDPR/PII, HR, taxes,
   lawsuits.
7. **When in doubt, keep it and note it.** Never invent dates, owners, categories
   or retention periods.

## Why these matter with Google Drive specifically

- Drive's "move" is destructive at the cloud boundary. The whole toolkit is built
  around **copy → verify → delete-to-trash**, never a bare move out of the cloud.
- Google-native files (Docs/Sheets/Slides) are cloud-only pointers. A "backup"
  that doesn't account for them silently loses content. See
  [`02-inventory.md`](02-inventory.md) and [`03-local-mirror.md`](03-local-mirror.md).
- The 30-day Drive trash is a **safety net, not a backup**. The real backup is a
  verified local mirror ([`03-local-mirror.md`](03-local-mirror.md)).

## The agent rules

If you drive this with an AI/automation agent, see [`../AGENTS.md`](../AGENTS.md) —
the operating rules (read-only first, copy never move, quarantine not trash,
CSV-reversible, small batches, verify before delete, confidentiality + flags).
