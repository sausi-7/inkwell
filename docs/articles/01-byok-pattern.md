---
title: "Your AI tool says 'BYOK.' Here are five questions that tell you if it's real."
subtitle: "A rubric for separating genuine Bring-Your-Own-Key from branded BYOK, scored across twelve tools."
publish_target: Medium (primary) · dev.to + Hackernoon (syndication D+2 / D+3)
status: draft-1
author: Saurabh Singh
last_updated: 2026-04-24
---

# Your AI tool says "BYOK." Here are five questions that tell you if it's real.

In late 2025, Cursor quietly killed BYOK.

If you were running the AI editor with your own OpenAI or Anthropic key, the phase-out hit over a few weeks. First you'd see an error you hadn't seen before: *"Agent and Edit rely on custom models that cannot be billed to an API key."* Regular completions against your key still worked. The premium features — the whole reason most people paid Cursor anything — did not. A quiet funnel onto the $20/month subscription. The [developer forum filled up](https://forum.cursor.com/t/byok-agents-perform-differently/154949). [Refund requests piled in](https://www.fintechweekly.com/magazine/articles/cursor-pricing-change-user-backlash-refund). Cursor issued a [public apology on July 4, 2025](https://www.fintechweekly.com/magazine/articles/cursor-pricing-change-user-backlash-refund) for the billing turbulence that preceded it. A visible share of users migrated to [Kilo Code](https://kilo.ai/landing/cursor), Aider, Continue, and Cline — tools that still honored the promise.

Here's the part that bothered me more than the removal itself: even while Cursor's BYOK had been active, [every request still routed through Cursor's backend for "prompt assembly"](https://www.cursor-ide.com/blog/cursor-custom-api-key-guide-2025). You were paying OpenAI or Anthropic directly for the inference, and Cursor was reading every prompt and every response on the way through.

That was still called "BYOK."

This is the core problem with the term. "Bring Your Own Key" has drifted into marketing shorthand for *"you pay for the inference, and we define what that entitles you to."* Some implementations are honest. A lot are theater. There's no shared vocabulary for the difference — which is why tools with wildly different threat models and lock-in profiles all sit under the same badge on the pricing page.

After a few weeks of reading docs, privacy policies, GitHub issues, and a couple of leaked incident threads, I think there are five questions that reliably separate real BYOK from branded BYOK. I'll walk through each, score twelve tools you're probably using or evaluating, and end with the pattern the honest ones are converging on — and what it looks like in code.

---

## The five questions

If a tool claims BYOK, these are the only five things that matter. None of them are about features. All of them are about *where the trust boundary actually sits*.

**1. Where does the key live?**
Three options: the tool vendor's server-side database, the client's memory (browser `localStorage`, in-memory only), or local disk (OS keychain, config file, env var). Each has a different attack surface. A key sitting in the vendor's database is only as safe as the vendor's breach response. A key in your OS keychain is only as safe as your laptop. A key in `localStorage` is only as safe as your browser's security model against XSS.

**2. Who logs your prompts and completions?**
The tool can log. The model vendor can log. Both can log. Neither can log. "BYOK" doesn't tell you which. And honestly — for most people doing most work — the prompts are *more sensitive than the key*. A leaked key you rotate. A leaked codebase you can't un-leak. [Zero-data-retention (ZDR) policies](https://www.warp.dev/privacy) matter as much as key custody, arguably more.

**3. Is the provider abstraction hardcoded, pluggable, or user-configurable?**
A tool locked to one provider is a BYOK illusion. You're not bringing *your* key — you're bringing *their* key format. Real BYOK lets you switch from GPT-5 to Claude Sonnet 4.7 to a local Ollama by changing one config value. If swapping the provider requires forking the tool, it isn't BYOK; it's single-vendor-with-receipts.

**4. Who absorbs cost volatility?**
The question everyone forgets. If a frontier model's per-million token price jumps 40% next quarter, whose margin takes the hit? If the tool charges a fixed subscription and you pay inference directly, *you* eat it (and can pin to a cheaper model tomorrow). If the tool resells inference with a markup, *they* eat it and may absorb-or-pass-through depending on their cap table. Real BYOK shifts cost volatility to the user, which is both a feature (optionality) and a responsibility (you need to watch pricing pages).

**5. What's the breach perimeter?**
If the tool vendor gets compromised next week, what of yours leaks? Keys only? Keys plus prompt history plus completion history plus file-tree context plus command transcripts? This is where most "BYOK" claims come apart — the key may be encrypted, but the prompts are usually sitting in a retention bucket somewhere *"for debugging."*

Ask every AI tool these five questions. The answers are rarely marketed, but they're usually documented somewhere if you look hard enough — in a privacy page footer, a GitHub issue from 2024, a changelog buried in the docs. Here's the current state.

---

## Scoring the field

Twelve tools, scored on the five questions, sources inline. I'm using **✅ honest**, **⚠️ qualified**, **❌ theater**. "Qualified" means the tool gets it mostly right with one caveat worth knowing.

| Tool | Key location | Prompt logging | Provider abstraction | Cost volatility | Breach perimeter |
|---|---|---|---|---|---|
| **[Aider](https://aider.chat)** | ✅ Local only (env/config) | ✅ None — direct to provider | ✅ Any LiteLLM-supported model | ✅ Fully on user | ✅ Keys + nothing else |
| **[Continue.dev](https://continue.dev)** | ⚠️ Was plain-text config ([issue #1729](https://github.com/continuedev/continue/issues/1729)); OS credential storage in recent builds | ✅ Direct to provider | ✅ Any provider via plugin | ✅ On user | ✅ Narrow |
| **[Cline](https://cline.bot)** | ✅ OS keychain | ✅ Direct to provider | ✅ Plugin-based | ✅ On user | ✅ Narrow |
| **[Zed AI](https://zed.dev/docs/ai/configuration)** | ✅ [OS credential storage](https://zed.dev/docs/ai/configuration) | ✅ Direct to provider | ✅ Any supported provider | ✅ On user | ✅ Narrow |
| **[OpenRouter](https://openrouter.ai)** (with BYOK) | ⚠️ Encrypted server-side | ⚠️ Doesn't log *by default*, but [samples small % for "anonymous categorization"](https://openrouter.ai/docs/guides/overview/auth/byok) | ✅ The whole point | ⚠️ 5% BYOK surcharge | ⚠️ Keys + a sampled prompt slice |
| **[Warp](https://warp.dev)** | ✅ [Local only, never synced](https://docs.warp.dev/support-and-community/plans-and-billing/bring-your-own-api-key) | ⚠️ ZDR with contracted providers; [cannot enforce ZDR for BYOK requests](https://www.warp.dev/privacy); command telemetry if opt-in | ⚠️ OpenAI / Anthropic / Google only | ✅ On user | ⚠️ Keys + telemetry envelope |
| **[VS Code "BYOK"](https://code.visualstudio.com/blogs/2025/10/22/bring-your-own-key)** | ✅ OS credential storage | ⚠️ Microsoft-level telemetry still applies | ✅ OpenAI, Anthropic, Gemini, OpenRouter, Azure, local | ✅ On user | ⚠️ Depends on your MS account |
| **[JetBrains IDEs](https://blog.jetbrains.com/ai/2025/12/bring-your-own-key-byok-is-now-live-in-jetbrains-ides/)** (Dec 2025) | ✅ OS credential storage | ✅ Direct to provider | ✅ Multiple providers | ✅ On user | ✅ Narrow |
| **[Claude Code](https://docs.litellm.ai/docs/tutorials/claude_code_byok)** | ✅ OS keychain (post-plugin rework) | ⚠️ Anthropic-vendor logging unless ZDR tier | ⚠️ Claude-first; BYOK via LiteLLM proxy | ✅ On user | ✅ Narrow |
| **[Cursor](https://cursor.com/help/models-and-usage/api-keys)** | ❌ Backend proxy — all prompts pass through Cursor | ❌ Prompts assembled server-side; logging unclear | ❌ Custom-tuned models excluded from BYOK | ⚠️ Blended | ❌ Broad |
| **ChatGPT Teams / Enterprise** | ❌ N/A — single-vendor; no BYOK | ⚠️ Opt-out enterprise training | ❌ OpenAI only | ❌ OpenAI pricing | ⚠️ Contractual |
| **[Anthropic Managed Agents](https://www.anthropic.com/engineering/managed-agents)** (Apr 2026) | ❌ Anthropic-held in a platform vault | ⚠️ Vendor-side per contract | ❌ Claude-only, by design | ❌ Anthropic pricing + per-runtime-hour fee | ⚠️ Vault-wide |

A few things jump out if you stare at this matrix.

**The gold standard is smaller than the branded-BYOK field.** Aider, Cline, Zed, JetBrains (post-Dec 2025), Continue (in recent builds) all get five green checks — key-local, prompts-direct, provider-pluggable, cost-on-user, narrow breach perimeter. They share a profile: open source or OSS-friendly, treat the tool as a *passthrough*, and almost never touch the prompt.

**The middle tier — OpenRouter, Warp, VS Code, Claude Code — are honest about where the nuance is**, and that's fine. If you use OpenRouter, you know you're trading some provider-selection convenience for a 5% markup and a small sampling rate. That's a readable contract.

**The theater tier is where the damage lives.** Cursor's BYOK still touching every prompt on the way through is the loudest example, but it's not the worst. The worst are the tools that claim BYOK on the pricing page and then route your requests through a retention pipeline "for product quality" — you find this out when a former employee posts on HN two years later. I'm not going to name names here because it's mostly inference; take the rubric and run it yourself before paying.

**Anthropic Managed Agents is the interesting new category.** It isn't BYOK — it's the opposite: *managed key custody*, where Anthropic explicitly holds OAuth tokens in a [vault and routes MCP tool calls through a proxy](https://www.anthropic.com/engineering/managed-agents) so the agent never touches the token. This is a defensible design for enterprise deployments that need audit trails and credential rotation, but it's very much *not* "bring your own key." Calling it BYOK would be dishonest, and Anthropic doesn't.

---

## The emerging pattern

If you look at the tools that hit all five greens, they share a remarkably consistent architecture. It hasn't been given a name yet. Here's what it actually looks like:

1. **The key never hits the vendor's server-side database.** It lives in the client — OS keychain, browser `localStorage`, or a config file the user controls. The user is the sole custodian.
2. **The key travels as a per-request header or env var**, not a session token. Every call carries it; nothing server-side persists it between calls.
3. **The tool is a passthrough, not a gateway.** The prompt goes from the client to the model provider with the thinnest possible envelope. If the tool does enrich prompts (context, persona, tool specs), that enrichment happens on the client or in a stateless function that logs nothing.
4. **Provider abstraction is a first-class configuration surface.** One string swap (`LLM_MODEL=ollama/llama3` → `LLM_MODEL=claude-sonnet-4-7`) and the whole system switches. [LiteLLM](https://litellm.ai) has become the de facto shim for this; it's in Aider, Continue, Claude Code's BYOK proxy, and most of the OSS middle tier.
5. **The server logs nothing that names the user.** Request metrics can be aggregated for ops. Prompts and completions never are.

That's the pattern. It doesn't have a catchy name yet. Call it "real BYOK" for now, or "pass-through key custody," or wait six months for someone to write a better term. The important thing is it's a *specific architecture*, not a marketing phrase.

---

## What it looks like in code

This is the smallest honest implementation of the pattern in Python + FastAPI. No database, no state, no session — the key rides the request and is used once.

**Client side (in the browser):**

```javascript
// Key stored in localStorage. Lives in the user's browser, never touches
// our server between draft requests.
const apiKey = localStorage.getItem('llm_api_key');

async function draftReply(signalId) {
  const res = await fetch(`/api/signals/${signalId}/draft`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-LLM-Key': apiKey,  // Per-request header. Nothing persists.
    },
    body: JSON.stringify({ model: 'claude-sonnet-4-7' }),
  });
  return res.json();
}
```

**Server side (passthrough, no persistence):**

```python
from fastapi import APIRouter, Header, HTTPException
import litellm  # Provider abstraction — swaps OpenAI/Claude/Ollama.

router = APIRouter()

@router.post("/api/signals/{signal_id}/draft")
async def draft(
    signal_id: str,
    payload: DraftRequest,
    x_llm_key: str | None = Header(default=None),
):
    # The key is a function parameter. It is never assigned to a
    # module-level variable. It is never written to disk.
    # It exists only for the lifetime of this request.
    if not x_llm_key and not payload.model.startswith("ollama"):
        raise HTTPException(400, "API key required for this provider")

    response = litellm.completion(
        model=payload.model,
        messages=build_prompt(signal_id),
        api_key=x_llm_key,          # Passed to LiteLLM, then to the provider.
        # No "store this for logging" flag. No metrics hook touches
        # `x_llm_key` or `messages`. Verify this by grep.
    )
    return {"draft": response.choices[0].message.content}
```

That's it. About 30 lines. Notice what *isn't* here:

- No `save_key_to_session(key)` call.
- No `audit_log.record(prompt)`.
- No `db.insert("prompts", ...)`.
- No `client = OpenAI(api_key=OPENAI_KEY)` at module level (the anti-pattern that most tools grow into).

Real BYOK is not primarily a database schema choice. It's a *discipline*: at every layer, the question "does this function need to know the key beyond this call?" is answered *no*, and that answer is enforced by making the key a function argument rather than module state.

You can verify any tool's claim on this by grepping its server code for `api_key` references. If the key only appears as a function parameter and never as a module-level constant, session attribute, or database column, the tool is probably honest. If it appears as `self.api_key = key` in some AuthService class, you know where to look for the retention bucket.

---

## When BYOK is genuinely the wrong choice

Not every tool should be BYOK. The pattern has real failure modes.

**Team deployments with shared compliance requirements.** If your company needs a single audit trail for every AI interaction, scattered BYOK keys across laptops is an operational nightmare. Managed key custody (Anthropic's Managed Agents model, or your own central vault) is the correct answer here. Don't bolt BYOK onto a tool whose users need SOC 2 trails.

**Integrations where the tool provides genuine compute value beyond the model.** Cursor's custom-tuned models really are tuned variants. If the tool is doing meaningful IP work beyond routing to a frontier model, the economics of "bring your own key" stop working — you'd be paying inference for a model the tool doesn't own, which is why Cursor killed BYOK in the first place. Not defending the execution, but the underlying economic pressure was real.

**Consumer products where users can't be trusted with keys.** A consumer app launching on iOS with "bring your own OpenAI key" has a 2% conversion rate for a reason. Real people don't want to manage credentials. BYOK is a power-user pattern. Ship a free managed tier, then offer BYOK as the escape hatch for the developer / self-host crowd that demands it.

The honest argument against BYOK is not "it's harder to build" — it's not, once you adopt the discipline — it's "my users don't want the responsibility." Which is a fair product call. Just don't put "BYOK-friendly" on your marketing page if what you actually mean is "we accept the key; we still do whatever we want with the data."

---

## A framework, not a feature

The next time an AI tool's pricing page mentions BYOK, paste the five questions into a note and go look for the answers. Privacy policy, trust page, changelog, GitHub issues, HN threads. Most of the time you'll find them within an hour of reading. If you can't find them, that's the answer.

If you're building a tool, make the answers *obvious*. Link them from the marketing page. Put them in a `/trust` or `/security` URL that's one click from the homepage. Show the grep — *here is where the key is read, here is where it is used, here are the three lines of code that touch it.* Your sophisticated users will audit. The unsophisticated ones will feel the discipline even without reading the code.

"BYOK" as a single word will keep meaning both things — the real pattern and the marketing veneer — for at least a few more years. The rubric is how you tell them apart.

---

*The tool I've been using as one reference implementation of this pattern is [Inkwell](https://github.com/sausi-7/inkwell) — a small self-hosted outreach tool where the LLM key lives in browser `localStorage` and rides the `X-LLM-Key` header per request. MIT. The whole server is ~1,500 lines of Python; grep it for `api_key` and you'll see all thirteen references. Offered only as one example of the pattern in practice — not as a product pitch. Fork it and apply the rubric to your own tools.*

---

### Sources

- [Cursor "BYOK Agents Perform Differently" forum thread](https://forum.cursor.com/t/byok-agents-perform-differently/154949)
- [Cursor custom-model BYOK mechanics](https://www.cursor-ide.com/blog/cursor-custom-api-key-guide-2025)
- [Cursor's apology + refund thread (FinTech Weekly)](https://www.fintechweekly.com/magazine/articles/cursor-pricing-change-user-backlash-refund)
- [Cursor BYOK ban alternatives (APIDog)](https://apidog.com/blog/cursor-byok-ban-alternative/)
- [Aider — terminal-based BYOK pair programmer](https://aider.chat)
- [Continue.dev plain-text key storage issue #1729](https://github.com/continuedev/continue/issues/1729)
- [Cline — zero-markup BYOK](https://cline.bot/)
- [OpenRouter BYOK auth docs](https://openrouter.ai/docs/guides/overview/auth/byok)
- [Zed AI configuration](https://zed.dev/docs/ai/configuration)
- [Warp Bring Your Own API Key](https://docs.warp.dev/support-and-community/plans-and-billing/bring-your-own-api-key)
- [Warp privacy policy — BYOK & ZDR limits](https://www.warp.dev/privacy)
- [VS Code "Bring Your Own Key" Oct 2025](https://code.visualstudio.com/blogs/2025/10/22/bring-your-own-key)
- [JetBrains BYOK launch Dec 2025](https://blog.jetbrains.com/ai/2025/12/bring-your-own-key-byok-is-now-live-in-jetbrains-ides/)
- [Claude Code BYOK via LiteLLM](https://docs.litellm.ai/docs/tutorials/claude_code_byok)
- [Anthropic Managed Agents — credential custody](https://www.anthropic.com/engineering/managed-agents)
- [LiteLLM — provider abstraction layer](https://litellm.ai)
