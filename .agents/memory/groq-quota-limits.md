---
name: Groq daily token quota
description: Free-tier Groq API token-per-day (TPD) limits differ drastically by model size; large models exhaust quota fast on chat bots.
---

Groq's free tier caps tokens-per-day (TPD) per model. Large models like
`llama-3.3-70b-versatile` have a much lower daily cap (order of 100k tokens/day)
than smaller instant models like `llama-3.1-8b-instant` (much higher cap).

**Why:** A family/personal Telegram bot sending a full system prompt + chat
history on every message can burn through a 100k/day budget in a few hours,
causing intermittent `429 rate_limit_exceeded` errors that look like random
bugs/crashes but are actually quota exhaustion, not code failures.

**How to apply:** When a Groq-backed bot's replies fail with a generic/opaque
error, check Railway (or wherever it's hosted) deploy logs for a printed
exception string containing `rate_limit` / `429` before assuming a code bug.
If confirmed, either switch to a lighter model with higher TPD, trim the
system prompt / history sent per call, or add a friendly fallback message
distinguishing "quota exhausted, try later" from a real error.
