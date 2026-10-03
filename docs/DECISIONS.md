# Decisions

One entry per decision. Status is one of:

- **Open**: needs an answer from the team.
- **Default**: proposed and being followed until someone objects.
- **Decided**: confirmed by the team; who and when are recorded.

When a decision changes, edit its entry and add a line to its history; do not delete old entries.

## Summary

| ID | Question | Status | Current answer |
|---|---|---|---|
| D0 | Scope of the product | Decided | Any region with weak connectivity; the pipeline is region-independent |
| D1 | Submission cut-off | Decided | 2026-10-04 9:00 AM ET |
| D2 | First test region and languages | Decided | Samosir (Lake Toba, Indonesia); Indonesian; nobody on the team reads Indonesian |
| D3 | Channels in the hackathon build | Default | SMS only; voice is P2 |
| D4 | SMS gateway for the demo | Open | Recommended: Android phone gateway; else Twilio |
| D5 | LLM on the server | Decided / Open | Any API can be plugged in; default is a small open model on our GPU server. Which model: open (D14) |
| D6 | Traveller app technology | Decided | Hackathon demo: offline web app (PWA). Later: native Android app, built by Claude |
| D7 | On-device LLM for travellers | Default | Optional, last priority |
| D8 | Where the server runs for the demo | Default | GPU server (theubuntu) + temporary tunnel; Mac for development |
| D9 | Repository | Decided / Open | Private GitHub repo created; visibility and license at submission open |
| D10 | Team roles | Open | 4-person split in PLAN.md §7 |
| D11 | Contact real hosts in the test region | Open | Recommended: try 2–3, with consent |
| D12 | Product name | Open | Working name `offgrid-tourism` |
| D13 | Listing trust rules | Default | Host confirms by SMS; last-confirmed date; owner-only edits; phone shown only with consent |
| D14 | Which small model, and how it is served | Open | Recommended: test two models on the test set, pick by measured accuracy; serve with Ollama |

## D0. Scope of the product — Decided

The product is for any place with weak connectivity where local businesses lack online information. The pipeline must not depend on one region: everything place-specific goes in a region profile (`regions/<id>.json`). The first test region is only an example.

- Decided by Chris, 2026-10-03.

## D1. Submission cut-off — Decided

2026-10-04 9:00 AM ET, about 17 hours after this log was started (4 PM ET on Oct 3). The plan uses the 17-hour column of PLAN.md §6.

- Decided by Chris, 2026-10-03. History: an earlier planning session had said about 8 hours were left.

## D2. First test region and languages — Decided

- **Decision:** Samosir Regency (Lake Toba, North Sumatra, Indonesia); host messages in Indonesian; Batak Toba as a stretch; traveller side in English. Samosir is a test example only (D0).
- **Why:** the World Bank's Indonesia Tourism Development Project includes Lake Toba ([project document, 2018](https://documents1.worldbank.org/curated/en/839781527910281861/pdf/Indonesia-Tourism-PAD-05102018.pdf)); OpenStreetMap shows that listed food and lodging is concentrated in one area (REAL_WORLD_DATA.md); Indonesian is well supported by language models.
- **Consequence: nobody on the team reads Indonesian.**
  - Claude writes the test messages; they are labelled synthetic and AI-written.
  - Accuracy is scored on fields that can be checked without reading Indonesian: category, village, price, hours, consent answer.
  - The team cannot judge the English translations or how natural the messages are. The pitch says so. If any Indonesian speaker (outside the team is fine) can spot-check 5–10 messages, record who and how many.
- Decided by Chris, 2026-10-03. History: proposed by the earlier planning session.

## D3. Channels in the hackathon build — Default

- **Default:** SMS only for hosts and travellers; app for travellers.
- **Trade-off:** voice calls were in the original idea for hosts who cannot type well. Dropping voice removes the speech-recognition risk but weakens the inclusion story.
- **Recommendation:** SMS in P0; add voice in P2 if at least 4 hours remain after P0 (record the call, speech-to-text, same pipeline, delete audio). WhatsApp later.
- History: SMS-only proposed by the earlier planning session because of time.

## D4. SMS gateway for the demo — Open

| Option | For | Against |
|---|---|---|
| **Android phone as gateway** (open-source gateway app on a teammate's Android phone with a SIM) | No carrier registration; normal SMS prices; the same setup could run in a real village | Needs an Android phone with a SIM that stays on; app account set up by a teammate |
| **Twilio** (US number) | Well documented; receiving SMS works quickly | Replies to US phones may be blocked until A2P 10DLC or toll-free verification, which can take days; must test early |
| Simulator page only | Always works | Not a real phone in the demo |

- **Recommendation:** the simulator page is built either way. For real SMS, use an Android gateway if a teammate has an Android phone with a SIM; otherwise Twilio, and test a reply within the first 30 minutes.
- Accounts must be created by a team member.

## D5. LLM on the server — Decided / Open

- **Decision:** the server talks to language models through one interface (a "port"), so any provider can be plugged in by changing settings, not code. The default is a small open model running on our own GPU server (theubuntu, RTX 3070 with 8 GB of GPU memory), served over an HTTP API.
- **How:** one client for the OpenAI-compatible API format, which local servers (Ollama, vLLM, llama.cpp) and most hosted providers accept, plus an Anthropic client. Settings: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. With no model configured, the server runs on rules plus follow-up questions.
- **Open:** which model, and the serving software (D14).
- Decided by Chris, 2026-10-03.

## D6. Traveller app technology — Decided

- **Hackathon:** an offline web app (PWA) for the demo. It runs in any smartphone browser, keeps working in airplane mode after the first load, and needs no app store.
- **Later:** a native Android app. Nobody on the team builds Android apps, so Claude will write it after the hackathon. The PWA's data format (region pack) and search rules carry over unchanged.
- Decided by Chris, 2026-10-03.

## D7. On-device LLM for travellers — Default

- **Default:** optional and last. Offline search covers the common questions; a model download of hundreds of MB to several GB and the battery use are costs travellers in these places may not accept.
- If built: a small model only turns a free-text question into search filters; answers are built from listing rows.
- History: proposed by the earlier planning session.

## D8. Where the server runs for the demo — Default

| Option | For | Against |
|---|---|---|
| **GPU server (theubuntu) + temporary tunnel** | The model and the server sit on one machine; the Mac can sleep | The machine suspends when idle until a sudo setting is changed; it is offline right now |
| A laptop + temporary tunnel, model on theubuntu over Tailscale | Easy to watch logs | Laptop must stay awake with the lid open |
| A cloud host | Stable URL | Account setup; free tiers may sleep and miss webhooks |

- **Default:** develop on the Mac; run the demo server and the model on theubuntu, reachable from the internet through a Cloudflare quick tunnel (no account needed; the URL changes on restart).
- **Blocker (2026-10-03, 4 PM ET):** theubuntu is offline on Tailscale (last seen 3 days ago). Someone has to wake it, then Chris runs `ssh -t theubuntu 'sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target'` so it does not suspend overnight.
- **Fallback if it cannot be woken:** run a smaller model with Ollama on the Mac (Apple M5, 16 GB) and keep the Mac awake, or run on rules only.

## D9. Repository — Decided / Open

- **Decided:** private GitHub repo `Zycheng114514/offgrid-tourism`, created 2026-10-03 at Chris's request.
- **Open:** make it public at submission? License (MIT recommended if public)?

## D10. Team roles — Open

Proposed 4-person split in PLAN.md §7. Needs: team size, names, who knows mobile development.

## D11. Contact real hosts in the test region — Open

- **Recommendation:** if a teammate can reach 2–3 real businesses (e.g., guesthouses with a public WhatsApp number) and they agree, ask them to send one real report. One real message is stronger evidence in the pitch than many invented ones.
- Daytime in Indonesia (UTC+7) starts around 7–8 PM ET.
- Rules: explain the project, get consent to store and show their message, do not publish their number without consent.

## D12. Product name — Open

Working name `offgrid-tourism`. Low priority; the GitHub repo can be renamed later.

## D13. Listing trust rules — Default

Host confirms each listing by replying `1`; each listing shows the last-confirmed date; only the phone number that created a listing can edit or close it; a host's phone number is shown only with consent.

- History: proposed by the earlier planning session.

## D14. Which small model, and how it is served — Open

- **Limits:** must fit in 8 GB of GPU memory with room for context (about 8B parameters or fewer at 4-bit), handle the host language, and return JSON that follows the listing schema.
- **Candidates:** general multilingual models (Qwen2.5-7B-Instruct, Qwen3 4B/8B, Gemma 3 4B) and Southeast Asia–specific models (SEA-LION, Sahabat-AI). Which ones handle Indonesian SMS well is not yet measured.
- **Recommendation:** run one general and one regional model on the same test set and keep the better one; the general model is the default for other regions. Serve with Ollama (installs without sudo, accepts a JSON schema for output, OpenAI-compatible API).

