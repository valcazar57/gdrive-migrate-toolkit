# Prior art & alternatives

Before building this, it's worth knowing what already exists — and why none of it,
on its own, solved the hard parts of a multi-account Google Drive / Workspace
reorganization.

## The one thing that made it possible

The whole method hinges on one specific capability that **almost no Drive client
has**:

- **Server-side copy/move *between accounts* that preserves Google-native files**
  (`rclone copy --drive-server-side-across-configs`), and
- **server-side *reparent* within one account** (`rclone move`), which is instant
  and also keeps natives editable.

Everything else (the inventory-without-hanging, the two-pass evacuation, reversible
verification) is method built **on top of** that capability. So the engine is
rclone; the value of this repo is the **method** (see [PLAYBOOK.md](../PLAYBOOK.md)),
because no packaged tool ties it together.

## Comparison

| Tool | Useful here? | Why |
|---|---|---|
| **rclone** | ✅ The one we use | The core of everything: sync, mirror, server-side move/copy, preserves natives, handles non-owned files and throttling. Indispensable. |
| **GAM** (Google Apps Manager) | 🟡 Partial | Strong for Workspace admin: transfer **ownership** and move files between users of the **same domain** via admin (more "official" than rclone for that). But: heavy admin / service-account setup, and it **does not cross distinct Workspace domains** (e.g. two different company domains). Helps only if everything is in one org and you want ownership transfer. |
| **rclone-webui-react** | 🟡 Cosmetic | Just a GUI for rclone. Adds convenience, not capability. |
| Generic `gdrive-migrate` rclone-wrapper scripts | 🟡 Marginal | Scripts that wrap rclone — i.e. what this repo is. Possibly a starting template, nothing more. |
| Official Workspace CLIs | ❌ (doubtful) | [INFERENCE] Official Workspace CLIs target admin/config, not bulk file moves that preserve natives. They don't fit an entity-by-entity reorg. |
| Single-account Go clients (e.g. `glotlabs/gdrive`) | ❌ | One-account upload/download/list. No server-side cross-account, no sync. Inferior to rclone here. |
| `goodls` | ❌ | Downloads public shared links. Doesn't migrate or reorganize accounts. |
| `google-drive-ocamlfuse` | ❌ | Mounts Drive as a filesystem on Linux. A FUSE mount hits the same hydration problems; this work was on Windows + Drive for Desktop. |
| Older terminal clients (`odeke-em/drive`, `prasmussen/gdrive`) | ❌ | Single-account, dated/archived. Superseded by rclone. |

## Bottom line

None of these, alone, solves what actually cost the effort: **preserving
Google-native files across accounts**, **avoiding the Drive-for-Desktop hydration
hang on Windows**, **contention / throttling (HTTP 429)**, and the **reversible
verification discipline**. rclone provided the pieces; the method tied them
together. That's why packaging it as a repo adds something new — there was no
off-the-shelf "merge / evacuate / reorganize these Drives" solution.
