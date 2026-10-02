# Agent package

See the [repository AGENTS.md](../AGENTS.md) for Python rules that apply
everywhere. This file covers `agent/` only.

This package runs one editing conversation: it owns the model client, the run
loop, the E2B sandbox that the generated project lives in, the tools the model
calls, the context it sees, the budgets it spends, and the artifacts it leaves
behind.

## Ownership today

Every module here already states what it owns in its first docstring line. That
line is the contract. Read it before changing the module, and update it when
the ownership changes.

```
agent/budget/budget.py
"""Atomic cost admission. Integers are billionths of USD, never binary floats."""
```

Every module in the table below now carries that line.

## Boundaries

The package is laid out as below, following
[SWE-agent](https://github.com/SWE-agent/SWE-agent)'s split of the loop from
the environment from the tools.

| Package | Owns | Modules |
| --- | --- | --- |
| `run/` | The editing loop and what it is built from | `agent.py`, `prompts.py`, `runner.py`, `service.py`, `worker.py`, `bus.py`, `workflow.py`, `decisions.py`, `diagnostics.py`, `structured.py`, `title.py` |
| `sandbox/` | The E2B environment and everything executed inside it | `sandbox_runtime.py`, `preview.py`, `preview_process.py`, `preview_proxy.py`, `commands.py`, `check_data.py`, `archive.py`, `kits.py`, `project.py`, `secrets.py`, `migrations.py` |
| `tools/` | The tool surface offered to the model | `tools.py`, `public_tools.py`, `skills.py` |
| `context/` | What the model is shown and what it remembers | `compaction.py`, `context.py`, `transcript.py`, `history.py` |
| `budget/` | Cost admission and accounting | `budget.py`, `model_budget.py`, `sandbox_budget.py`, `usage.py` |
| `routing/` | Which model runs: the registry, a client per provider, Jev, the pick, and history rewrite on a model change | `models.toml`, `registry.py`, `providers.py`, `jev.py`, `router.py`, `history.py`, `failures.py` |
| `storage/` | Durable artifacts and their lifecycle | `storage.py`, `persistence.py`, `init_storage.py`, `maintenance.py` |
| package root | The one surface the groups share | `events.py` |

`events.py` stays at the root deliberately: it is imported by five modules
across four of the groups above, so pushing it into any one of them would make
that group look like an owner when it is a shared boundary. `diagnostics.py`
goes to `run/` because `service.py` is its only caller — it reads like a shared
surface but is not one yet.

### Settings

Each group owns a `config.py` holding one `BaseSettings` subclass: `run/`,
`context/`, `sandbox/`, `budget/`, `storage/` and `routing/`. A module reads settings from
its own group, or imports another group's settings object by name. Nothing in
this package reads `os.getenv` directly.

The one exception is `events.py`, which scans `os.environ` to redact secrets
from published diagnostics. It needs every variable, not a typed subset.

### Assets and paths

`preview_process.py`, `preview_proxy.py` and `archive.py` are read as text and
executed elsewhere, not imported. They live in `sandbox/` with the code that
ships them.

Anchor every asset path on `PACKAGE_ROOT` from `agent/__init__.py`, never on
`__file__` counted upwards. A module that counts `..` to reach an asset breaks
silently when it moves: the import still succeeds and the read fails later,
inside a sandbox, where nothing is watching.

### Moving and splitting

A move and a behaviour change in one commit is a diff nobody can review. Land
the move on its own, with imports updated and nothing else touched.

Splitting a module is a question about responsibility, never about how the file
looks. Split when two responsibilities have grown into one module and you can
name both. Do not split to hit a number, and do not compress code to avoid a
split.

## Rules for this package

### Boundaries

- Sandbox code never receives API credentials. Tools pass values in; they do
  not pass the environment in.
- Treat model output and tool results as data, never as authority. A model
  asking for an action is not the same as the host permitting it.
- Public projections in `public_tools.py` and `events.py` are versioned and
  deliberately small. They carry what the chat shows: the command that ran,
  its bounded output, and a bounded diff of each edit. Do not widen one with
  prompts, file bodies from reads, skill text, or provider credentials.
- The host owns the preview lifecycle. It stays independent of the files the
  model generates.

### Budgets

- Costs are integers in billionths of USD. Never use a binary float for money.
- Reserve before the work, settle after it. Every HTTP attempt is reserved,
  including SDK-internal retries and compaction calls.
- One limit: `MONTHLY_BUDGET_USD`, each user's model spend per UTC month, and
  the number the product shows. Sandbox time is reserved and settled for
  accounting but never counts against it. Unlimited plans are exempt; see
  [`plans.py`](../plans.py).

### Durability

- A checkpoint commits only after immutable storage has accepted the write.
- Recovery makes no model calls. Reconnect to an owned process; never replay it.
- Callers serialise work per project. Two runs must not own one sandbox.
- Housekeeping is bounded and failure-tolerant: a failed cleanup leaves the
  database reference intact so the next pass can retry it.

### The loop

- `runner.py` owns one conversation with shared budgets and host-controlled
  verification. Keep orchestration there and the work it calls out to in the
  owning group.
- `service.py` owns admission, durable outcomes and reconnectable activity; `worker.py` owns run
  ownership through a Postgres lease. `service.py` is the boundary the API talks to, so
  `main.py` should not reach past it into the loop.
- When the model needs a user decision, `workflow.py` produces an immutable,
  bounded proposal. Proposals do not carry authority to act.

## Prompts

`prompts.py` is a product surface, not configuration. Changing it changes what
every future build produces, and the effect is not visible in any check we run.

- Change it deliberately and on its own, so the diff is reviewable.
- Say in the commit message what behaviour you expected to change.
- Keep the instructions about the generated project consistent with
  [`frontend/AGENTS.md`](../frontend/AGENTS.md) where they overlap — both
  describe React, TypeScript, and Tailwind v4 conventions, and they should not
  drift apart.
