# Inkwell on Reddit — the builder's outreach playbook

> For entrepreneurs and builders who are tired of cold-DM SaaS bills, generic LLM slop, and outreach that doesn't sound like them. Inkwell is free, open-source, runs on your machine, and drafts in *your* voice. This is how we sell it on Reddit.

---

## The pitch in one sentence

> **Free Reddit outreach that finds real buyers and writes in your voice — not ChatGPT's. Self-hosted, MIT, bring your own LLM key.**

That's the hook. Every title, every comment, every README line should ladder back to three promises:

1. **Better outreach** — you reply where people are actually asking for help, not cold-DM a scraped list.
2. **Free forever** — scans cost nothing (rule-based, zero tokens). Drafting uses *your* OpenAI/Claude/Ollama key, on-demand only.
3. **Your voice** — persona YAML + your own example comments. Readers can't tell it came from a model because functionally it didn't — it came from *you*, faster.

Entrepreneurs don't buy "AI tool." They buy leverage, cost savings, and voice. Sell those.

---

## Why entrepreneurs and builders will care

The target reader is someone who:
- Is building a product and knows their customers hang out on Reddit / HN / IndieHackers
- Has tried Apollo / Lemlist / Lemwarm / Zopto and churned because it felt gross
- Pays $29–$200/mo for "AI outreach" tools and isn't seeing ROI
- Can write well themselves — they just don't have time to lurk 15 subs every morning

**What Inkwell gives them:**

| They have today | Inkwell replaces it with |
|---|---|
| 45 min/morning scrolling Reddit | 60-second scan, top signals ranked Yes/Maybe/No with reasons |
| $49/mo SaaS outreach subscription | $0. BYOK means you pay only your own LLM bill, and only when you draft |
| Generic AI replies that scream "bot" | YAML persona + your example comments → replies that sound like you |
| Cold-DM blasts that get ignored | Warm replies to people who *literally just asked* for help |
| Data locked in a vendor | MIT license, self-hosted, your data on your disk |

That table is the post. That table is the tweet. That table is the README hero.

---

## The Postiz proof point

[Postiz](https://postiz.com) is the existence proof we're modeling after. Solo founder, open-source, launched on Reddit, [re-launched monthly with genuine updates](https://stackstarts.com/open-source-playbook-how-nevo-built-postiz-17k-mrr/), hit **$14k MRR, 584k Docker pulls, 15k GitHub stars**. Same audience mix Inkwell targets: [r/selfhosted, r/indiehackers, dev.to, Hackernoon](https://www.indiehackers.com/post/i-did-it-my-open-source-company-now-makes-14-2k-monthly-as-a-single-developer-f2fec088a4).

What worked for them — and what will work for Inkwell:

- **Every feature shipped = an excuse to re-launch.** New scanner, new exporter, streaming drafts, auto-persona — each is a post.
- **README *is* the landing page.** GIF at the top, install in one block, screenshots below. No separate marketing site.
- **Engage for hours after each post.** First 2 hours decide if you hit the front page. Reply to every comment within 5 minutes.
- **Docker Compose + MIT + public roadmap.** Removes every "can I trust this?" question.

Inkwell already has the structural pieces: MIT license, protocol-based plugins, 17 open contributor issues, persona scaffolding, FastAPI + plain HTML UI. The playbook runs.

---

## Assets to ship before you post

Non-negotiable. Without these, the posts underperform.

| Asset | Why it sells | Status |
|---|---|---|
| **GIF: scan → Yes/Maybe/No table → click Draft → reply in your voice** | Doubles upvotes on r/SideProject. This is the sales demo. | ⚠️ [Issue #17](https://github.com/sausi-7/inkwell/issues/17) |
| **3 screenshots** — home, profile, scan results | Subs that don't render video need fallback | ⚠️ [Issue #17](https://github.com/sausi-7/inkwell/issues/17) |
| **README hero: GIF + one-line pitch + install block** | The repo is the landing page | ✅ Partial — put GIF at the top |
| **Docker Compose** | r/selfhosted won't take you seriously without it | ❌ Ship before posting there |
| **3+ real personas** in `config/personas/` | "Will it sound like me?" is the #1 objection. Seeing filled-in examples answers it. | ⚠️ Have 1 (indie-hacker). Need 2 more. |
| **17 open issues with acceptance criteria** | Signals you want contributors, not just stars | ✅ Done |
| **MIT license + contributor templates** | Removes legal friction, signals "you can fork this" | ✅ Done |

**Do not post until GIF + Docker Compose + ≥3 personas exist.** These three assets are the difference between "looks like a real tool" and "looks like a weekend hack."

---

## Subreddit matrix — where entrepreneurs and builders hang out

Ranked by fit. Self-promo rules verified April 2026.

| Sub | Subs | Fit | Self-promo | Notes |
|---|---|---|---|---|
| **r/SideProject** | 240k | 🟢 Perfect | ✅ Encouraged | Founder-friendly. Must include stack, lessons, pricing. |
| **r/indiehackers** | 115k | 🟢 Perfect | ✅ Share Your Project Saturdays | Dedicated promo day, no karma gate |
| **r/selfhosted** | 500k | 🟢 Perfect | ⚠️ Lead with value | Needs Docker. Privacy-first angle wins. |
| **r/LocalLLaMA** | 266k | 🟢 Strong | ⚠️ 10% cap | Lead with Ollama, not OpenAI. Price-conscious audience. |
| **r/Entrepreneur** | 3.8M | 🟡 Medium | ⚠️ Strict | Huge but mods nuke promo. Only post if a question-thread invites it. |
| **r/SaaS** | — | 🟡 Medium | ⚠️ Karma history helps | Fine if you frame as "anti-SaaS" alternative |
| **r/Python** | 1.4M | 🟡 Tolerant | ⚠️ "Show r/Python:" prefix | Lead with architecture, not pitch |
| **r/smallbusiness** | 1.8M | 🟡 Worth trying | ⚠️ Cautious | Frame as "how I replaced my $600/year SaaS stack" |
| **r/programming** | 6M | 🔴 Skip | ❌ LLM content banned April 2026 | Don't waste the post |

### Sub-specific angles

**r/SideProject** — [members smell low-effort pitches](https://www.mediafa.st/marketing-on-rsideproject). Lead with the GIF, the stack, and what you *learned* building it. Pricing + license stated up front.

**r/indiehackers** — [Share Your Project Saturdays](https://redditagency.com/subreddits/r/indiehackers) is the explicit promo slot. Frame indie-to-indie: "I built the tool I wish existed when I was doing outreach for my last launch."

**r/selfhosted** — [lead with value, not the product](https://www.reddit-radar-marketing.com/guides/r/selfhosted). Docker-first, privacy-first. Inkwell's "binds to 127.0.0.1, BYOK key in localStorage, no telemetry" story is native fit.

**r/LocalLLaMA** — [10% self-promo cap, price-conscious audience](https://gummysearch.com/r/LocalLLaMA/). Ollama is the hero. Lead with "zero API cost, runs on llama3.2" and the sub will carry you.

**r/Python** — ["Show r/Python:" prefix, architecture over pitch](https://www.conbersa.ai/learn/best-subreddits-for-developers). Lead with protocols, FastAPI, no-framework UI. AI content is tolerated when the lead is technical depth.

**r/smallbusiness & r/Entrepreneur** — reply to existing threads where someone asks "how do I do outreach without sounding spammy?" rather than posting cold. Link to the repo once, as a recommendation, never as a lead.

---

## The five posts

Each title is ≤300 chars and sells *on its own* — don't rely on the body. Bodies are 250-400 words, Reddit-native voice, [GIF above the fold](#assets-to-ship-before-you-post).

### Post 1 — r/SideProject (Day 1, Tue 8:30 AM ET)

**Title:**
> I was paying $49/mo for an outreach tool that felt like spam. Built the opposite — Inkwell: scans Reddit free, drafts replies in your voice, MIT, self-hosted.

**Body:**

```
Hey r/SideProject,

Every outreach SaaS I tried (Apollo, Lemlist, Lemwarm, a few AI ones)
felt the same: a cold-DM engine with an AI wrapper. I didn't want to
blast 500 strangers. I wanted to find the handful of Reddit posts
each week where I could actually help someone in my niche — and
reply as myself, not as "Hi I hope this email finds you well."

So I shipped Inkwell. Three promises:

1) Scanning is FREE. Rule-based scoring — no LLM tokens — surfaces
   Yes / Maybe / No signals with a one-line reason per post. Scan
   15 subs every morning, pay $0.

2) Drafting is in YOUR voice. You define a persona (bio, tone,
   3+ real comments you've actually written). When you like a signal,
   click "Draft" — your own OpenAI/Claude/Ollama key writes a reply
   that sounds like you. It sounds like you because it's prompted on
   you.

3) You stay in the loop. No auto-posting, no scheduling, no mass
   anything. Inkwell shows you the draft. You edit. You send.
   The tool makes you faster. It doesn't pretend to be you.

[GIF: scan → 3-column Yes/Maybe/No table → click Draft → reply
appears in the modal]

Stack: Python + FastAPI + plain HTML/CSS/JS (no framework, no build
step). LiteLLM under the hood — swap OpenAI / Claude / Ollama with
one env var. Self-hosted on 127.0.0.1. MIT licensed. Docker Compose
ready.

What I learned shipping it:
- The persona YAML went through 7 drafts. "Your voice" is hard to
  specify until you try. 3 real example comments beats any instruction.
- Reddit's rate limit is brutal. Two-phase scan (fetch → rule-filter
  → hydrate only survivors) took scan time from 10 min to ~60s.
- The biggest win wasn't the AI, it was making scans free. Once
  tokens stopped per-scan, I actually ran it every day.

Roadmap: auto-persona from your comment history, HN scanner, daily
email digest, local LoRA voice model. 17 good-first-issues are open
if you want to ship a feature.

Repo: https://github.com/sausi-7/inkwell

Genuinely want feedback, especially if you've bounced off the SaaS
outreach tools. What would make you actually run this on Monday?
```

**First comment (post 5 min after OP, pinned context):**
> The reason I went MIT + BYOK instead of SaaS: outreach that works compounds with *your* voice, not a vendor's templates. If I locked the persona in my DB and charged $29/mo, I'd have built exactly the thing I was trying to avoid. You own the tool, the persona, and the key. Forever. Happy to go deep on the architecture — the README has the full diagram.

---

### Post 2 — r/selfhosted (Day 3, Thu 9:00 AM ET)

**Title:**
> Inkwell — self-hosted outreach tool. Replaces your $49/mo Lemlist/Apollo subscription. Scans Reddit free, drafts with your own LLM key. Docker, MIT.

**Body:**

```
If you're tired of paying cloud-only outreach SaaS a monthly fee to
do something your laptop can do: Inkwell runs entirely on your
machine.

- Python 3.11+ FastAPI app, binds to 127.0.0.1 by default
- No accounts, no signup, no telemetry, no cloud-call-home
- Your LLM key lives in browser localStorage — never hits the server
  except as an X-LLM-Key header on draft requests (passed straight
  to LiteLLM, never persisted or logged)
- Scans, personas, and drafts all stored as local JSON
- Works end-to-end on Ollama for fully air-gapped operation
- MIT licensed — fork it, modify it, ship your own variant

The architectural split that made free scans possible:
- analyzers/rules.py — deterministic heuristic scoring. ZERO tokens.
  Scan 15 subs every morning, $0 forever.
- analyzers/voice.py — LLM drafting. Called ONLY when you click
  "Draft" on a specific signal you liked.

The old version combined both in every scan and was burning $10/day.
Splitting them turned it into a tool I actually run daily.

Stack:
- Python + FastAPI + Jinja2 + vanilla HTML/CSS/JS (no framework)
- LiteLLM for provider abstraction (OpenAI / Claude / Ollama / any)
- requests for Reddit's public JSON API (no OAuth, no PRAW)
- APScheduler (wired for the upcoming daily-digest feature)

[GIF / screenshots]

Install:

  git clone https://github.com/sausi-7/inkwell
  cd inkwell && python3 -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  python -m inkwell serve

Docker Compose ships this week. Open http://localhost:8000.

Same design philosophy as running your own Plausible / Umami /
Cal.com — you own the stack, you own the data, no lock-in.

Repo: https://github.com/sausi-7/inkwell
Roadmap: https://github.com/sausi-7/inkwell/blob/main/docs/ROADMAP.md
```

---

### Post 3 — r/indiehackers Share Your Project Saturday (Day 5, Sat 10:00 AM ET)

**Title:**
> After churning from 3 outreach SaaS tools in a row, I built the opposite — free Reddit outreach that writes in YOUR voice. Open-source, BYOK.

**Body:**

```
Fellow builders — this is the tool I wish had existed when I was
doing outreach for my last product.

The problem: my customers lived on Reddit and IndieHackers. They
posted when they were stuck. A thoughtful reply at the right moment
turned into a customer conversation maybe 1-in-5 times. That's huge.

But the workflow was broken:
- Manual: open Reddit at 8am, scroll for 45 min, find 1-2 good
  posts, get distracted, close the tab
- SaaS outreach tools: cold-DM engines wearing an AI hat. Not even
  adjacent to what I wanted.

Inkwell flips the category.

Starts with REAL signals (public posts where someone says "I'm
stuck" or "what do y'all use for X"). Scores them with transparent
rule-based heuristics — Yes / Maybe / No with a one-line reason.
No tokens spent. Free scans, forever.

See a signal worth replying to? Click Draft. Your own OpenAI or
Ollama key generates a reply in MY voice — prompted on a YAML
persona (bio, tone, 3+ real comments I'd written).

Then I edit, copy, send. As myself. Like a human.

Why this matters for indie outreach specifically:
- You're not paying $49/mo to talk to 10 people per week.
- Your reply doesn't sound like every other LLM-generated comment
  on Reddit right now, because it's prompted on YOU.
- Scans compound. Every morning you see new signals. Warm
  replies > cold DMs, every time.
- No lock-in. MIT license, BYOK, self-hosted. You own your voice.

Tech (for the curious):
- Python + FastAPI + plain HTML/CSS/JS, no React, no build step
- Protocol-based scanners — HN scanner is ~100 LOC and the issue
  has full specs, someone could ship one this afternoon
- 17 good-first-issues open with acceptance criteria + file lists

Repo: https://github.com/sausi-7/inkwell

Open question: for indie outreach specifically, what's your
best-performing channel right now? Reddit's been my wedge — curious
if others are finding different signal.
```

---

### Post 4 — r/LocalLLaMA (Day 8, Tue 8:30 AM ET)

**Title:**
> Inkwell — free outreach tool that runs fully on Ollama. Zero API cost, zero cloud calls, writes in your voice via YAML persona.

**Body:**

```
Most "AI outreach" tools assume you're fine paying OpenAI forever.
You're not. Neither am I.

Inkwell is a self-hosted Reddit scanner + voice-drafting tool that
runs end-to-end on Ollama (or any LiteLLM-compatible provider).

The pitch for this sub specifically:

- Scans use ZERO LLM tokens. Rule-based heuristic scoring in plain
  Python. Scan every morning, run it on a cron, do whatever —
  it costs nothing.
- Drafting uses whatever LiteLLM can reach. Set
  LLM_MODEL=ollama/llama3.2 in .env and you're done. Nothing
  leaves your machine. No API keys. No subscription.
- Your voice = YAML persona (bio, dos, don'ts, 3+ example
  comments in your own words). Model is *prompted* on your
  persona — no fine-tune needed to start. Tested with:
    - llama3.2:3b — snappy, carries tone surprisingly well
    - mistral-small:24b — noticeably better on longer example
      comments
    - qwen2.5-coder:7b — great when your persona is technical
- Self-hosted FastAPI, binds to 127.0.0.1. BYOK key stays in
  browser localStorage, never touches disk.

[GIF of a draft generation via Ollama]

Roadmap I'd love this sub's input on:

1) LoRA fine-tune once you have 50+ approved drafts — your voice
   becomes a small adapter on a 7B base. Free drafts forever,
   no prompt-engineering dance. Probably unsloth + transformers.
2) Streaming drafts token-by-token via litellm streaming mode —
   same model, way better perceived latency.
3) Auto-persona from your Reddit/HN comment history — pull 200
   comments, fit a persona, skip the manual YAML step.

Stack: Python, FastAPI, plain HTML/CSS/JS, MIT.
Repo: https://github.com/sausi-7/inkwell

Which local model has worked best for you on "match my voice"
(vs generic text gen)? Tuning the prompt block for different
size classes and I'd love real signal.
```

---

### Post 5 — r/Python (Day 10, Thu 9:00 AM ET)

**Title:**
> Show r/Python: Inkwell — free outreach tool. FastAPI + LiteLLM + plain HTML/CSS/JS, zero frameworks, zero build step, protocol-based plugins.

**Body:**

```
Open-source Python tool for finding and replying to posts where
people are asking for help — scans are free (heuristic rules),
drafts are BYOK on-demand.

But the bits r/Python might actually enjoy are the architectural
choices, so I'll lead with those:

1) typing.Protocol for scanners / exporters / filters
   - No base class, no registry boilerplate, no inheritance
   - A Scanner is "anything with name: str and scan(targets,
     max_age_hours, emit=None) -> list[RawSignal]"
   - Adding a HackerNews scanner is ~100 LOC. Contributors
     don't have to grok a DI container.

2) No frontend framework. No bundler.
   - Jinja2 templates + vanilla JS modules, one per page
   - Each HTML file is ~150 lines you can actually read
   - "Plain JS with a tiny helper namespace" is enough for
     SSE streaming + fetch + localStorage + a draft modal
   - Debugged an SSE framing bug in 5 minutes. Would have
     taken an hour in React.

3) Analyzer split that made scans free
   - analyzers/rules.py — pure Python heuristics. Deterministic,
     testable, zero tokens.
   - analyzers/voice.py — only code path that touches an LLM.
     Called on-demand when the user clicks "Draft." Takes
     model + api_key as arguments (not env) so the web UI
     passes a per-request key from browser localStorage.
   - Old pipeline did both in one LLM call per scan. Splitting
     was ~1 day's work and turned a $10/day tool into a free one.

4) Two-phase scan with SSE progress
   - fetch posts (fast) → rule-filter (free) → cap top 10 per
     sub → hydrate comments ONLY for survivors
   - Rate-limit events bubble through fetch_json(emit=...) to
     an SSE stream so the UI shows "⏳ Reddit rate-limited,
     waiting 10s" instead of going silent during backoff
   - threading.Timer 5s heartbeat so the browser knows the
     worker is alive even when Reddit is throttling hard

5) Tests: 51, pytest-only, no fancy fixtures
   - Conftest has one factory; everything else is vanilla
   - Rule-based scorer is 100% deterministic → every branch
     gets a plain Python test

[Screenshot: scan page + architecture diagram]

Use case for anyone who missed the pitch: if you're a builder
doing outreach on Reddit/HN/IH, Inkwell scans for real
help-wanted posts, scores them free (no LLM), and drafts replies
in your voice using your own key — on demand. No SaaS bill.

MIT licensed, 17 open issues with acceptance criteria. Designed
for someone to ship a scanner / exporter / persona in an
afternoon.

Repo: https://github.com/sausi-7/inkwell

If you're into "boring Python tools you'd enjoy reading" — would
love a second pair of eyes on the architecture. What would you
have done differently?
```

---

## First-hour playbook (every post)

From the research: [Show HN and Reddit launches live or die on engagement velocity in the first hour](https://www.everydayailab.xyz/blog/lessons-from-ai-tool-launches).

- **Minute 0** — post goes up.
- **Minute 2–5** — drop your first-comment seed. Pin context, end with one open question that invites replies.
- **Minute 5–60** — reply to every comment within 5 minutes. Even "nice." Every reply is ≥2 sentences and adds something — acknowledge, then expand or ask back.
- **Hour 1–2** — go deep on real concerns (privacy, threat model, "how is this different from X?"). These comments convert lurkers. If someone has a great idea, open a GitHub issue *in real time* and link it: *"Great call, opened #18 — feel free to chime in."*
- **Hour 2–8** — check every 20 min. Cross-link comments to existing issues. If traffic's spiking, draft Show HN for the morning.
- **Hour 8–24** — diminishing returns but still respond. This is where you get the long, thoughtful comments from people who read the repo.

---

## Objection playbook (copy-paste-ready, edit before pasting)

### "Aren't you just going to flood Reddit with AI slop?"
> Fair worry. Inkwell doesn't post anything — it surfaces a signal and drafts a reply in your voice. You read, edit, decide, send. The persona system takes 3+ *real* comments you've actually written as examples, so the draft is prompted on you, not on a generic model. If you want to stress-test the "is this my voice?" question, clone it and plug in your own examples. MIT.

### "How is this different from Apollo / Lemlist / [contact DB tool]?"
> Those start with a contact list and push messages out. Inkwell starts with public signals (posts where someone just said "I'm stuck") and helps you respond in place, in your voice. Opposite direction — signal-first vs. contact-first. BYOK + self-hosted means nothing leaves your machine.

### "Why not just read Reddit manually?"
> For 3-5 subs you probably should. The wedge is when you're watching 10-15 subs for a narrow pattern ("help request in my niche"). Inkwell pre-filters to the ~5 posts per sub per day that actually score, with transparent reasons. 90% time savings on the skim, and signals compound across days.

### "What does this actually cost me?"
> $0 for scans, forever. For drafting you pay your own LLM provider — Ollama is free; gpt-4o-mini is maybe a cent per draft; Claude Haiku similar. Compare to $29–$200/mo for the SaaS outreach tools and it's not close.

### "Why MIT instead of AGPL?"
> I want people to fork this, integrate it into their own workflows, and modify freely. The moat isn't license enforcement — it's the persona marketplace and contributor ecosystem. MIT compounds faster.

### "What about Reddit's ToS? Ban risk?"
> Reddit's public JSON API is accessed without auth for scanning — explicitly fine, no developer agreement needed. Drafting is local. Your replies go through the normal Reddit UI under your own account, edited by you. If you ever use the CLI to get a draft and paste it, that's no different than using ChatGPT in another tab.

### "Persona YAML seems like a lot of work."
> Short-term, yeah — I ship a `_template.yml` and a filled-in `indie-hacker.yml` you can fork. Long-term, issue #15 (auto-persona from your comment history) is the killer feature: paste your Reddit username, Inkwell fits a persona from your last 200 comments, you review and save. 30 seconds. Targeting next release.

### "Can I trust the BYOK claim?"
> Inspect the code. Key lives in browser localStorage under `ink_llm_key`, travels only on draft requests as `X-LLM-Key` header, server passes it straight to LiteLLM and does not persist or log it. Grep for `api_key` — it's always a local variable. MIT, audit away.

---

## 14-day launch calendar

Hit the sweet spots: [Tuesday–Thursday US morning](https://redditagency.com/blog/best-time-to-post-reddit), rotate subs, 2+ hours on each thread.

| Day | Time (ET) | Sub | Angle |
|---|---|---|---|
| **Tue (D1)** | 8:30 AM | r/SideProject | Founder story, anti-SaaS pitch |
| **Thu (D3)** | 9:00 AM | r/selfhosted | Replace your Lemlist subscription |
| **Sat (D5)** | 10:00 AM | r/indiehackers (SYPS) | Indie-to-indie, outreach that compounds |
| **Tue (D8)** | 8:30 AM | r/LocalLLaMA | Ollama-native, zero API cost |
| **Thu (D10)** | 9:00 AM | r/Python | Architecture showcase |
| **Tue (D12)** | 8:30 AM | **Show HN** | Parallel track (see below) |
| **Sat (D14)** | Anytime | dev.to + Hackernoon | Long-form writeup, repo cross-link |

Gaps are intentional. Reddit's spam filter compares notes across subs, and [the 90/10 contribution rule](https://redship.io/blog/reddit-self-promotion-rules-2026) expects you to actually participate between launches.

**Off-days**: comment on *other people's* posts in the same subs. Answer Docker questions in r/selfhosted, Ollama config in r/LocalLLaMA, pricing and positioning in r/SideProject. Earn the right to be there.

---

## Show HN parallel track (Day 12)

Different beast, different rules. [Show HN title format](https://news.ycombinator.com/showhn.html) is strict.

**Title:**
> Show HN: Inkwell – Free outreach tool that drafts in your voice. BYOK, self-hosted

[Post Tue/Wed/Thu 8–10 AM ET](https://www.myriade.ai/blogs/when-is-it-the-best-time-to-post-on-show-hn). Your repo *is* your landing page — [HN rewards GitHub links over marketing sites](https://www.lucasfcosta.com/blog/hn-launch).

**Body** (HN values terseness):

```
Inkwell scans forums for posts where you can genuinely help, then
drafts replies in your voice — using your own LLM key, only when
you ask for one. Scanning is rule-based and free; voice drafting
is the only code path that uses tokens.

Built it because every outreach tool I tried felt like a cold-DM
machine with an AI wrapper. This is the opposite: signal-first,
human-in-the-loop, self-hosted, no lock-in, no SaaS bill.

Stack: Python + FastAPI + plain HTML/CSS/JS (no framework).
LiteLLM for provider abstraction — OpenAI / Claude / Ollama / any.
MIT.

Architecture split worth calling out:
- analyzers/rules.py — deterministic scoring, zero tokens
- analyzers/voice.py — LLM drafting, BYOK, on-demand only
- Protocol-based scanners/exporters — HN scanner is ~100 LOC
- Two-phase scan with SSE progress + rate-limit event surfacing

Repo has 17 open issues with acceptance criteria for contributors.
Happy to discuss design choices in the comments.

https://github.com/sausi-7/inkwell
```

**First comment (2 min after OP):**

> Three things I'd love HN feedback on:
> 1. Persona-as-YAML vs. fine-tuning — I'm betting prompting + 3-5 real examples gets 80% of the way. Right tradeoff?
> 2. Heuristic scoring vs. local embeddings for signal detection — I went with transparent rules; bge-small is on the table for v2. How have others made this call?
> 3. BYOK via X-LLM-Key header — any attack surface I'm missing with key-in-browser-only?

---

## Monthly cadence (the Postiz loop)

[Postiz re-launched monthly with a genuine update](https://stackstarts.com/open-source-playbook-how-nevo-built-postiz-17k-mrr/). Not the same post — each carried a new story.

| Month | Hook | Primary sub |
|---|---|---|
| **M1 (now)** | "I built it" — founder story | r/SideProject, r/selfhosted |
| **M2** | Auto-persona from comment history | r/indiehackers |
| **M3** | HN scanner lands (community PR) | r/LocalLLaMA, r/Python |
| **M4** | Streaming drafts + Product Hunt | r/SaaS (if karma earned) |
| **M5** | Daily email digest + scheduler | r/selfhosted |
| **M6** | Local LoRA voice model | r/LocalLLaMA |

Every monthly post has (1) a new feature, (2) a lesson learned, (3) a visible nod to a community contributor. The contributor shout-out is how you turn visitors into a community.

---

## What NOT to do

- ❌ Post to 5 subs in 24 hours — Reddit flags duplicate self-promo.
- ❌ "I'm excited to announce..." — any marketing-ism kills it on sight.
- ❌ Emojis in titles (🚀, ✨, 🎉) — reads as LinkedIn.
- ❌ Link to a marketing site first. [The repo is the landing page](https://www.markepear.dev/blog/dev-tool-hacker-news-launch).
- ❌ Post and ghost. If you can't sit on the thread for 2 hours, reschedule.
- ❌ Argue with downvoters. Respond once, factually. Move on.
- ❌ Use Reddit's crosspost feature. Write a fresh post per sub.
- ❌ Buy upvotes or DM friends for upvotes. Reddit detects it fast.
- ❌ Post to r/programming — [LLM content banned April 2026](https://www.tomshardware.com/tech-industry/artificial-intelligence/the-largest-programming-community-on-reddit-just-banned-all-content-related-to-ai-llms-r-programming-is-prioritizing-only-high-quality-discussions-about-ai).
- ❌ Oversell on r/SaaS or r/Entrepreneur. Mods are aggressive — earn karma first.

---

## Success metrics (per post)

Be honest about what "good" looks like.

| Metric | Bad | Okay | Good | Front page |
|---|---|---|---|---|
| Upvotes in 1h | <5 | 10–30 | 50–100 | 200+ |
| Comments in 1h | <3 | 5–15 | 20–40 | 50+ |
| GitHub stars in 24h | <10 | 20–80 | 150–400 | 500+ |
| Docker pulls / installs | — | — | measurable | spike |

[A successful Show HN drives 500–2,000 GitHub stars in 24h](https://fansgurus.com/blog/grow-github-stars-8-methods). Your first post won't. Your third or fourth might.

---

## Pre-launch checklist

- [ ] GIF in README above the fold (issue #17)
- [ ] 3 screenshots in `docs/screenshots/` and linked in README
- [ ] `docker-compose.yml` tested on a clean machine
- [ ] 3+ filled-in personas under `config/personas/`
- [ ] All 17 open issues reviewed and still accurate
- [ ] `.env.example` up to date
- [ ] `python -m inkwell serve` works from a fresh venv on a fresh clone
- [ ] `pytest` passes green
- [ ] README opens with: one-line pitch → GIF → install block → "Who is this for" → "What it costs ($0 scans, BYOK drafts)"
- [ ] README has a "Security & BYOK threat model" section
- [ ] Repo About on GitHub: description, topics, homepage
- [ ] CONTRIBUTING.md + issue + PR templates present

---

## References (verified April 2026)

- [r/programming LLM content ban — Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/the-largest-programming-community-on-reddit-just-banned-all-content-related-to-ai-llms-r-programming-is-prioritizing-only-high-quality-discussions-about-ai)
- [Reddit tightening AI-bot verification — TechCrunch](https://techcrunch.com/2025/05/06/reddit-will-tighten-verification-to-keep-out-human-like-ai-bots/)
- [r/SideProject marketing guide — MediaFa.st](https://www.mediafa.st/marketing-on-rsideproject)
- [r/SideProject stats — Hive Index](https://thehiveindex.com/communities/r-sideproject/)
- [r/selfhosted marketing guide — Reddit Radar](https://www.reddit-radar-marketing.com/guides/r/selfhosted)
- [r/LocalLLaMA stats — Gummy Search](https://gummysearch.com/r/LocalLLaMA/)
- [r/indiehackers community guide — Reddit Agency](https://redditagency.com/subreddits/r/indiehackers)
- [Reddit self-promotion rules 2026 — Redship](https://redship.io/blog/reddit-self-promotion-rules-2026)
- [Show HN Guidelines — official](https://news.ycombinator.com/showhn.html)
- [Show HN timing research — Myriade](https://www.myriade.ai/blogs/when-is-it-the-best-time-to-post-on-show-hn)
- [Best time to post on Reddit 2026 — Reddit Agency](https://redditagency.com/blog/best-time-to-post-reddit)
- [Postiz open-source playbook — StackStarts](https://stackstarts.com/open-source-playbook-how-nevo-built-postiz-17k-mrr/)
- [Postiz monthly-launch strategy — Indie Hackers](https://www.indiehackers.com/post/i-did-it-my-open-source-company-now-makes-14-2k-monthly-as-a-single-developer-f2fec088a4)
- [Show HN launch mechanics — Lucas F Costa](https://www.lucasfcosta.com/blog/hn-launch)
- [Dev tool HN launch guide — Marke Pear](https://www.markepear.dev/blog/dev-tool-hacker-news-launch)
- [AI tool Show HN lessons — Everyday AI Lab](https://www.everydayailab.xyz/blog/lessons-from-ai-tool-launches)
- [GitHub stars growth — Fansgurus](https://fansgurus.com/blog/grow-github-stars-8-methods)

---

*Last updated: April 24, 2026. Re-verify subreddit rules before each post — the AI-content landscape shifts monthly.*
