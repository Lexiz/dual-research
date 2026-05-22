# Spec templates

As of spec 0152, spec templates are typed. Pick the right one for the work:

| Type | Use when | Template |
|---|---|---|
| **new-feature** | Adding capability, new UI/UX, new endpoint | [`_templates/new-feature.md`](_templates/new-feature.md) |
| **bug** | Fixing something that doesn't work | [`_templates/bug.md`](_templates/bug.md) |
| **refactoring** | Restructuring without behavior change | [`_templates/refactoring.md`](_templates/refactoring.md) |
| **test** | Adding coverage to existing code | [`_templates/test.md`](_templates/test.md) |
| **breaking** | Removing or changing an existing contract | [`_templates/breaking.md`](_templates/breaking.md) |

In normal operation you do **not** copy a template by hand. The `/spec-draft`, `/spec-queue`, and `/spec-promote` skills choose the right template and populate it from the current conversation. See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for the full lifecycle.
