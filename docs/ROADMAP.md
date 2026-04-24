# Roadmap

Opinionated, ordered. Shipping one thing at a time — not a wishlist.

## ✅ Shipped

- **Multi-provider LLM** — OpenAI, Claude, Ollama, anything LiteLLM supports
- **Analyzer split (BYOK)** — scans are free; voice drafting is on-demand, key-in-browser
- **Web UI** — Profile builder, settings (output + BYOK + filters), scan runner with live SSE progress
- **Two-phase scan** — fetch posts → rule-filter → cap → hydrate comments only for survivors; rate-limit and heartbeat events surfaced to the UI
- **Persona marketplace foundations** — `config/personas/` with template + first contribution

## 🎯 Next (shipping soon)

- **Auto-persona from post history** — Paste a Reddit / HN username → Inkwell fits a persona from the last ~200 comments. Removes the single biggest friction in onboarding.
- **Daily email digest** — APScheduler cron → top-N signals delivered to your inbox each morning.
- **Streaming drafts** — Token-by-token via LiteLLM streaming. Same tokens, much better perceived speed.

## 🔜 Soon

- **Hacker News scanner** — Algolia API, no auth
- **Product Hunt scanner** — GraphQL API
- **Dev.to scanner** — public REST API
- **Notion exporter** — signals → Notion database
- **Airtable exporter** — signals → Airtable base
- **Slack webhook exporter** — `Yes`-ranked signals → Slack channel
- **Feedback loop** — 1–5 star ratings on signals feed back into `ai_preferences` weighting

## 🌅 Later (bigger bets)

- **Local fine-tuned voice model** — After 50+ approved drafts, train a LoRA adapter on a 7B model. Your voice runs locally — free drafts forever, no API lock-in.
- **Browser extension** — *Reply in my voice* button next to Reddit / HN comment boxes, talks to your local Inkwell.
- **Cross-platform identity graph** — Same person on Reddit, HN, Twitter → avoid double-outreach. Local-only.
- **Agent mode (opt-in)** — "Find 5 posts this week about Postgres; draft; wait for my approval in Slack." Long-running local agent.

## Anti-goals

Things we're **not** building, on purpose:

- ❌ A SaaS / hosted version with our own LLM keys (defeats the BYOK pitch)
- ❌ Mass-DM / cold-email features (there's enough of that already; not the product we want to exist)
- ❌ Framework migration (React / Vue / Svelte) — plain HTML/CSS/JS stays; the whole point is readable, forkable, no build step
- ❌ A contact database (we're signal-first, not contact-first)

## How to influence the roadmap

- Open a **[feature request](https://github.com/sausi-7/inkwell/issues/new?template=feature_request.md)** — we triage weekly
- Upvote what you want in **[Discussions](https://github.com/sausi-7/inkwell/discussions)**
- Ship a PR — the fastest way. See **[docs/GOOD_FIRST_ISSUES.md](GOOD_FIRST_ISSUES.md)** for concrete starter tickets.
