---
name: skill-creator
description: "Create a new skill for this project from a workflow, convention or standard the user wants followed every time. Use when the user says make a skill, create a skill, turn this into a skill or save this workflow, or describes a repeatable way of building something they want applied in every build, even without the word skill. Do not use for one-off changes to the app."
---

# Skill Creator

A skill is a reusable set of instructions the builder applies whenever a request matches it. This
skill writes one into the project, where it is always on.

## 1. Understand the repeatable part

From the request and the conversation, find:

- **Trigger**: the kind of request that should bring the skill in.
- **Scope**: what the skill covers.
- **Boundary**: what it must not be used for.
- **The method**: the steps, rules and examples to follow every time.

Ask one short question only when the trigger is unclear enough to change what the skill does.
Otherwise write the skill from what the user said.

## 2. Choose the name

- Lowercase letters, numbers and hyphens, at most 64 characters, for example `brand-voice`.
- Not starting with `anthropic-` or `claude-`, and not the name of a skill already in the catalog.
- Short and specific: the user types it after `/` to call the skill on purpose.

## 3. Write the file

Write exactly one file with `write_files`: `.agents/skills/<name>/SKILL.md`, where the folder is the
name. Its first lines are the frontmatter:

```
---
name: <name>
description: <one line>
---
```

- `name` must equal the folder name.
- `description` is one line of at most 1024 characters. Start with "Use when", then name the
  trigger, the scope and the boundary. The builder decides when to use the skill from this line
  alone, so make it specific.

After the frontmatter, write the instructions in Markdown:

- Imperative steps and rules, in the order to follow them.
- A short example where it removes doubt.
- Under 500 lines. No secrets, keys or personal data.

## 4. Finish

- Do not change the app's own files for this request unless the user also asked for that.
- Tell the user, in plain product language, that the skill is saved in this project and always on,
  that they can type `/<name>` to use it on purpose, and that Manage skills in the `/` menu can save
  it to their library so every project gets it.
