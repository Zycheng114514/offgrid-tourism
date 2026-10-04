# Plan and pipeline

中文版：[PLAN.zh.md](PLAN.zh.md)


## 1. What we are building

Small food and lodging businesses in places with weak connectivity are often missing from online maps and booking sites. Their owners may only have a feature phone. Travellers who go there cannot find out where to eat or sleep.

- **Hosts** (local businesses) report what they offer by SMS from any phone, in their own language. The server turns each message into a structured listing (place, what, price, hours, contact) and keeps the original text plus an English translation.
- **Travellers** download listings for a village or district while they have a connection, then search them on their phone with no connection at all. They can also ask in their own words: with data the server answers from the listings, with only a cellular signal the same works by SMS, and with no connection a small model on the phone helps the search (in progress).

## 2. Design principles

1. **The pipeline is region-independent.** Everything specific to a place (languages, currency, keywords, village list, reply texts, phone format) lives in a region profile file (`regions/<id>.json`). Adding a region means writing a new profile, not changing code. Samosir, Indonesia is only the first test profile.
2. **Use AI only where fixed rules cannot do the job:** turning free-text messages into fields, and translation. Keywords, prices, hours, phone numbers and village names are parsed by rules first.
3. **The traveller side works with zero AI.** Offline search over a small region pack answers most questions instantly on any phone and costs almost no battery. An on-device model is optional and last.
4. **Ask instead of guessing.** If a required field is missing, the server asks the host one short SMS question, like a survey, rather than letting a model fill it in.
5. **Every listing is confirmed by its host.** The server texts back a summary; the host replies `1` to confirm. Each listing shows when it was last confirmed. A phone number can only edit its own listings.
6. **Consent before publishing.** A host's phone number is shown to travellers only if the host agreed.
7. **Any model can be plugged in.** The server reaches language models through one interface; the default is a small open model on our own GPU server, and a hosted API can replace it by changing settings.
8. **Claims are measured or labelled.** Every number in the pitch is either measured by a script in this repo or marked as an estimate.

## 3. Region profiles

A region profile (example: [`regions/samosir.json`](../regions/samosir.json)) defines:

| Field | Example (Samosir test profile) |
|---|---|
| Area for OpenStreetMap queries | `Samosir`, admin level 5 (regency) |
| Host languages | Indonesian (`id`); Batak Toba (`bbc`) as a stretch |
| Traveller languages | English |
| Currency and shorthand | IDR; `25rb` = 25,000; `1,5jt` = 1,500,000 |
| SMS keywords | `MAKAN` (food), `INAP` (lodging), `TUTUP` (closed), `BUKA` (open), `CARI` (search) |
| Village list (gazetteer) | from OpenStreetMap place points, later the official village list |
| Reply templates | confirmation and follow-up questions in Indonesian |
| Phone format, timezone | `+62`, `Asia/Jakarta` |

## 4. Pipeline

### 4.1 Host side: message → listing

```
Host phone (SMS)                                   [no voice in this build]
   │
   ▼
Android phone with SIM running an SMS gateway app ──► POST /webhooks/sms
   │
   ▼
1. Identify sender      phone number → host record (create on first message)
2. Detect intent        keyword rules (MAKAN / INAP / TUTUP / 1 / CARI …) from the region profile
3. Parse fields         rules first: price, hours, phone, village name (fuzzy match to gazetteer)
4. Extract the rest     LLM fills remaining fields from free text into the listing schema,
                        through the LLM port (§4.5); with no model configured, rules only
5. Validate             JSON Schema + checks (price range, village exists, hours valid)
6. Ask if missing       one SMS question per missing required field (name, village, what, price)
7. Translate            keep original text; add English (LLM, or a translation model)
8. Confirm              SMS back: summary + "Balas 1 jika benar" (reply 1 if correct)
9. Store                SQLite: listing + original message + English + extraction method;
                        voice audio is never stored
```

Required fields: category, name, village, what is offered, price (or "ask"), hours (or "ask"). Optional: capacity, landmark, photo-free description, phone-publish consent.

### 4.2 Traveller side: four ways to get answers

| Connection | How the traveller asks | What answers |
|---|---|---|
| Data (at a hotspot) | App downloads the region pack | Server export: JSON per village or district |
| None | Search in the app | Local filters on the pack: category, village, price, open now, distance (GPS works offline). No AI. |
| Cellular only | SMS `CARI makan Garoga` or free text | Server matches listings, replies with the top 3 in at most 2 SMS (160 characters each, plain characters only) |
| Data | Ask in their own words, in the app | Rules pick candidate listings; the server's LLM answers from them only and cites listing IDs; the answer is checked, otherwise rules build it (`server/offgrid/chat.py`) |

**In progress:** a small on-device model (Qwen2.5-0.5B-Instruct, running in the browser) that only turns a free-text question into search filters. Answer text is built from listing rows, so the model cannot invent places.

A search that starts with a search word (`SEARCH`, `CARI`, `搜索`) stays pure rules. Questions in free words, in the app or by SMS, are answered from the listings by the server's model (simulated in this demo), with rules as the fallback.

### 4.3 Data

- **Listing record:** [`schemas/listing.schema.json`](../schemas/listing.schema.json).
- **Region pack:** `{region, generated_at, villages[], listings[]}`, only confirmed listings, phone numbers only with consent. Expected size: kilobytes per village.
- **Message log:** every inbound and outbound SMS with timestamps, for debugging and evaluation.

### 4.4 Where AI is used

| Step | Method | AI? | Without an LLM key |
|---|---|---|---|
| Intent, price, hours, phone | Rules from the region profile | No | Same |
| Village name | Fuzzy match to gazetteer | No | Same |
| Free-text fields | LLM with the listing schema | Yes | Ask the host the missing questions by SMS |
| Translation to English | LLM or translation model | Yes | Show the original only |
| Traveller SMS questions | Keyword parse, LLM for free text | Partly | Keyword format only |
| Traveller questions (app and SMS) | LLM over the candidate listings, then checks | Yes | Answer built from the listing rows by rules |
| Offline search | Filters on the pack | No | Same |

### 4.5 The LLM port

All model calls go through one function: `complete_json(task, text, schema) -> dict`. Behind it:

| Provider setting | Talks to | Use |
|---|---|---|
| `openai_compatible` | Any server that speaks the OpenAI API format: Ollama, vLLM, llama.cpp; most hosted APIs | A later deployment, e.g. Qwen3-1.7B |
| `anthropic` | Anthropic API | Optional hosted alternative |
| `simulated` | A file of example messages with outputs written in advance | **The hackathon demo**: no model runs |
| `none` | Nothing | Rules plus SMS follow-up questions |

Settings live in `.env` (`LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`). Prompts are files in `models/prompts/`, one per task (extract listing, translate, parse traveller question, answer from rows), so they can be changed and re-scored without touching code.

## 5. Hackathon scope

**P0, the core demo (must have):**
- Server: SMS webhook, rules + LLM extraction, follow-up questions, confirmation, SQLite, traveller SMS search, region pack export.
- Web demo: a host-side page (a basic phone plus what the server did) and a traveller-side app; both work without the SMS gateway.
- Traveller app as an offline web app (PWA): download a pack, search offline, call or SMS a host. A native Android app comes after the hackathon.
- Example host messages with model outputs written in advance.
- Seed data for the test region: real village names and landmarks, invented businesses and phone numbers.
- Region profile for the test region.

**P1 (needed for a credible pitch):**
- Measured accuracy on a labelled test set (Section 9).
- Real-world data page with measured numbers ([REAL_WORLD_DATA.md](REAL_WORLD_DATA.md)).
- Slides and demo video.

**P2 (only if time is left):**
- Weekly SMS asking hosts "still open? reply 1".
- On-device small model for free-text questions.
- A second language or a second region profile, to show region independence.

## 6. Timeline

Cut-off: 2026-10-04 9:00 AM ET, so the 17-hour column applies. The 8-hour column is kept as the fallback if we fall behind. Hours count from the start of the build.

| Hours | Deadline 9:00 AM ET Oct 4 (≈17 h) | If only ≈8 h are left |
|---|---|---|
| 0–3 | Server P0 + simulator page; gateway app on the Android phone | Server P0 + simulator |
| 3–6 | Real SMS working end to end; PWA offline search; seed data | PWA offline search; seed data |
| 6–9 | Demo pages polished; real-world numbers on slides | Slides + video from the simulator |
| 9–12 | Slides, demo video, README for judges | Submit |
| 12–15 | P2 items if P0/P1 are done | — |
| 15–17 | Buffer, submit | — |

## 7. Work items (the team assigns people)

| Item | Who |
|---|---|
| Server, LLM port, extraction prompt, region pack export, web app, synthetic test set, scoring script, deploy script | Claude |
| Install the SMS gateway app on an Android phone with a SIM; keep it charged and online | Team |
| Pick the model | Chris |
| Check the web app on real phones, including airplane mode; record the demo | Team |
| Connectivity and visitor data for the test region (REAL_WORLD_DATA.md §2–3) | Team |
| Slides and demo video | Team |

## 8. Demo script (about 3 minutes)

Pages: `/pipeline` (the pipeline step by step), `/host` (host side), `/app/` (traveller side).

1. The gap, with measured numbers from OpenStreetMap for the test region.
1a. The pipeline walkthrough (`/pipeline`, Play): one example SMS through rules, model, checks and follow-up questions to a traveller's search; then the example where the model invents a name and the check rejects it.
2. A host texts `MAKAN Warung Bu Sinaga di Garoga, nasi ikan 25rb, buka 7-21` from a basic phone to the gateway phone's number. The server replies with a summary; the host replies `1`. A second, free-text message shows the fields a model would fill (model output written in advance and labelled as such).
3. A traveller's app downloads the Garoga pack, then the phone goes into airplane mode. Searching "cheap food open now" still works and shows the listing with "confirmed today".
4. A traveller with no data texts `CARI makan Garoga` and gets 3 listings by SMS.
5. Measured accuracy, limits, and how to add a new region.

## 9. Evaluation

| What | How | Output |
|---|---|---|
| Extraction accuracy | Not reported: no model runs, and scoring outputs we wrote ourselves would measure nothing | — |
| Traveller SMS search | 15 questions with the expected listings | % where the right listing is in the top 3 |
| Pack size and offline search | Real phone, airplane mode | KB per village; search time; works yes/no |
| Cost | SMS count per listing; LLM tokens per message | Cost per listing |

All example messages are invented by Claude and labelled synthetic. The automated tests (`server/tests`) check that the pipeline works end to end on them; they are not evidence of accuracy on real messages. No model is run or compared.

## 10. Risks

| Risk | Plan |
|---|---|
| Gateway phone loses power, signal or the app stops | Keep it charged and on Wi-Fi; the simulator page is the fallback |
| Model too slow on a CPU-only server | Reply to the gateway at once and send the SMS when the model finishes; keyword messages skip the model; switch to Option A |
| Nobody on the team reads Indonesian | Score only fields that can be checked without reading it; label test messages as AI-written |
| The demo server goes down | Restart with `deploy/deploy.sh`; the tunnel address then changes |
| Small model returns broken JSON or wrong fields | Constrain output with the JSON schema; validate; ask the host by SMS when a field fails |
| Laptop sleeps or tunnel URL changes | Keep the lid open; update the webhook URL after restarts |
| Wrong or stale listings | Host confirmation, last-confirmed date, only the owner's number can edit |

## 11. Who already does this

Closest overlaps first. Items marked (not re-checked) come from memory and were not re-verified today; we have not searched for this exact combination yet, and not finding something does not mean it does not exist.

- **World Bank Indonesia tourism project:** created online profiles for more than 20,000 businesses; no income results reported (World Bank 2025 ten-year tourism review, from our literature notes).
- **Government tourism-village platforms**, e.g. Indonesia's Jadesta directory of tourism villages (not re-checked).
- **Google Maps, booking sites and OpenStreetMap:** already list the busy tourist centres; offline map apps (Organic Maps, OsmAnd) show OSM places with no connection (not re-checked).
- **SMS crowdsourcing to a database or map:** Ushahidi, FrontlineSMS (not re-checked).
- **Feature-phone voice platforms where locals record reports:** Gram Vaani's Mobile Vaani, CGNet Swara in India (not re-checked).
- **SMS to a cloud AI service, deployed:** Jacaranda Health PROMPTS (Kenya), Babyl (Rwanda) in health (from our case review, 2026-10-03).

Our difference is in the details and is unverified: hosts list themselves by SMS in their own language; listings are confirmed and dated; travellers get region packs that work offline; the same pipeline is reused for any region through a profile.

## 12. After the hackathon

- Pilot with a local tourism group or village office that can seed the first listings (a one-time visit or survey) and promote the SMS number; hosts then keep listings current by SMS.
- A local number or short code through a local SMS provider; decide who pays for host SMS.
- Measure intermediate outcomes first (listings created and kept current, traveller searches, calls to hosts). Our literature notes found no causal evidence that putting small businesses online raises their income in developing countries, so the pilot should measure that rather than assume it.
