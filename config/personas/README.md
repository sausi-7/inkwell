# Persona Templates

This directory holds community-contributed persona files — drop-in `personality.yml` alternatives that capture different voices.

## Why a marketplace?

The whole product is built around *your* voice. But most people don't know how to write a good persona from scratch. The fastest way to teach people is to show them working examples.

Contribute a persona if you've found a voice that consistently produces good drafts — your future self will thank you, and so will the next person trying to get started.

## Using a persona template

1. Pick a file from this directory (e.g. `indie-game-dev.yml`).
2. Copy its contents to `config/personality.yml`, or in the web UI visit `/profile`, click *Import*, and paste.
3. Edit to fit you — change the bio, swap out the example comments, keep what feels right.

## Contributing a persona

1. Copy `_template.yml` to `<your-handle>.yml` (e.g. `ana-technical-founder.yml`).
2. Fill it in. Minimum bar:
   - A concrete bio (2 sentences max)
   - 3+ example comments — **real ones you've actually written** beat any synthesized example
   - Specific `donts` (not "sound natural" — that's not actionable)
3. Open a PR. In the PR description, briefly say who this voice is useful for (indie game dev? technical founder? community manager?).

## Schema

Same as `config/personality.yml`:

- `name` — how the persona refers to itself (first name is fine)
- `bio` — one short paragraph
- `interests` — topics you talk about
- `expertise` — topics you speak to with conviction
- `tone.style` / `tone.humor` / `tone.formality` — short phrases
- `dos` — list of specific things to do
- `donts` — list of specific anti-patterns
- `example_comments` — 3+ comments in this voice (the single highest-leverage field)
