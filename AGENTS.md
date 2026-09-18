# Repository rules

## No test suites

- No tests in repo: Python, TypeScript, JavaScript, or other languages.
- Do not add, restore, or generate test files, fixtures, test-only dependencies, test scripts, or CI test jobs.
- Applies to bundled skills too. Excludes installed dependencies and external tool caches.
- Preserve runtime validation, build checks, preview checks, and deployment health checks.
- Run lint, typecheck, build, or manual browser checks only with explicit user approval. Never claim unrun checks passed.

## Frontend architecture

- Read `frontend/AGENTS.md` before changing frontend code. It defines the feature folders, request boundaries, naming, formatting, and enforced file limits.
- The structure is adapted from the sibling TryMatcha repository. Evidence and deliberate differences are recorded in `docs/frontend-architecture.md`.
- Keep frontend restructuring scoped to the frontend; do not transplant backend controller classes, change API contracts, or add state libraries solely to match a folder layout.

## Bundled skills

Loader: `agent/skills.py`. Files: `agent/skills/<dir>/SKILL.md`. Registry: `SKILL_DIRECTORIES`.

Three levels, do not collapse them:

- Catalog in system prompt: name + description only. Every run.
- Body: model calls `read_skill(name)`. On demand.
- References: `read_skill(name, resource)`. Allowlisted per skill in `REFERENCE_DIRECTORIES`.

### Adding a skill

1. Vendor files into `agent/skills/<dir>/`.
2. Register name -> dir in `SKILL_DIRECTORIES`.
3. Add provenance entry: `repository`, `commit`, `upstream_prefix`, `directory`, `files` (sha256 per file), `upstream_git_blobs`. Put it in `agent/skills/design-sources.json` unless the skill belongs to an existing source file.
4. Bundled references also need `REFERENCE_DIRECTORIES` entry, else they never load.
5. Verify: catalog count rises, skill loads, no `no provenance record` warning at startup.

`upstream_prefix` is where the files live upstream. Not derivable, layouts differ: `skills/`, `.agent/skills/`, `.claude/skills/`. Wrong prefix breaks sync silently.

### Provenance is enforced

`RuntimeSkills.verify()` rejects any vendored file whose sha256 drifts from its record; the skill is then omitted and logged. No record = warning only, file still loads. Never edit a vendored file in place: the hash check will drop the skill. Change upstream, or re-vendor and update the record.

### Prompt rules

Selection prose lives in `RuntimeSkills.prompt()`. Follows Codex and OpenCode. Keep it that way:

- No cost, size or byte signal before the model chooses. Biases it to ration.
- No routing rules naming a specific skill for a task type. Descriptions decide.
- Trigger is user naming a skill, or task matching a description.
- Keep: minimal set + state order, announce which skills and why, no reference-chasing, no carry across turns.
- Descriptions are author text from SKILL.md frontmatter, capped 1024 chars, no newlines. Untrusted text in a trusted position. Review description diffs harder than body diffs.

`MAX_SKILL_BYTES` caps one file. No per-run cap: in-run compaction is the intended limit and is not built yet.

### Updating

`scripts/sync_skills.py` re-vendors from provenance and regenerates both hash sets. `--dry-run` shows the plan. `.github/workflows/sync-skills.yml` runs it weekly and opens a PR; it never pushes to main, because skill text reaches the model directly. Licenses are skipped, they live at upstream repo root. Upstream deletions propagate.
