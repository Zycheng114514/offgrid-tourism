# Plan and pipeline

Status: draft for team review, 2026-10-03. Decisions referenced as D1, D2, … are in [DECISIONS.md](DECISIONS.md).

## 1. What we are building

Small food and lodging businesses in places with weak connectivity are often missing from online maps and booking sites. Their owners may only have a feature phone. Travellers who go there cannot find out where to eat or sleep.

- **Hosts** (local businesses) report what they offer by SMS from any phone, in their own language. The server turns each message into a structured listing (place, what, price, hours, contact) and keeps the original text plus an English translation.
- **Travellers** download listings for a village or district while they have a connection, then search them on their phone with no connection at all. With only a cellular signal they can ask by SMS. With data they can also chat with the server.

## 2. Design principles

1. **The pipeline is region-independent.** Everything specific to a place (languages, currency, keywords, village list, reply texts, phone format) lives in a region profile file (`regions/<id>.json`). Adding a region means writing a new profile, not changing code. Samosir, Indonesia is only the first test profile (D2).
2. **Use AI only where fixed rules cannot do the job:** turning free-text messages into fields, and translation. Keywords, prices, hours, phone numbers and village names are parsed by rules first.
3. **The traveller side works with zero AI.** Offline search over a small region pack answers most questions instantly on any phone and costs almost no battery. An on-device model is optional and last (D7).
4. **Ask instead of guessing.** If a required field is missing, the server asks the host one short SMS question, like a survey, rather than letting a model fill it in.
5. **Every listing is confirmed by its host.** The server texts back a summary; the host replies `1` to confirm. Each listing shows when it was last confirmed. A phone number can only edit its own listings.
6. **Consent before publishing.** A host's phone number is shown to travellers only if the host agreed.
7. **Claims are measured or labelled.** Every number in the pitch is either measured by a script in this repo or marked as an estimate.

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
Host phone (SMS)                                   [voice and WhatsApp: later, D3]
   │
   ▼
SMS gateway (Twilio or an Android phone gateway, D4) ──► POST /webhooks/sms
   │
   ▼
1. Identify sender      phone number → host record (create on first message)
2. Detect intent        keyword rules (MAKAN / INAP / TUTUP / 1 / CARI …) from the region profile
3. Parse fields         rules first: price, hours, phone, village name (fuzzy match to gazetteer)
4. Extract the rest     LLM fills remaining fields from free text into the listing schema;
                        if no LLM is configured, rules only (D5)
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
| Data | Chat in the app | Server LLM answers only from listing rows and cites listing IDs; it cannot add places that are not in the database |

Optional, last (D7): a small on-device model that only turns a free-text question into search filters. Answer text is built from listing rows, so the model cannot invent places.

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
| Online chat | LLM over listing rows | Yes | Not available; offline search still works |
| Offline search | Filters on the pack | No | Same |

## 5. Hackathon scope

**P0, the core demo (must have):**
- Server: SMS webhook, rules + LLM extraction, follow-up questions, confirmation, SQLite, traveller SMS search, region pack export.
- A web page that simulates a phone sending SMS, so the demo works even if the SMS gateway fails.
- Traveller app: download a pack, search offline, call or SMS a host.
- Seed data for the test region: real village names and landmarks, invented businesses and phone numbers.
- Region profile for the test region.

**P1 (needed for a credible pitch):**
- Measured accuracy on a labelled test set (Section 9).
- Real-world data page with measured numbers ([REAL_WORLD_DATA.md](REAL_WORLD_DATA.md)).
- Slides and demo video.

**P2 (only if time is left):**
- Voice reports: record the call, speech-to-text, then the same pipeline; delete the audio.
- Weekly SMS asking hosts "still open? reply 1".
- On-device small model for free-text questions.
- A second language or a second region profile, to show region independence.

## 6. Timeline

The cut-off is not yet confirmed (D1). Hours count from the start of the build.

| Hours | Deadline 9:00 AM ET Oct 4 (≈17 h) | If only ≈8 h are left |
|---|---|---|
| 0–3 | Server P0 + simulator page; SMS gateway account; app skeleton | Server P0 + simulator |
| 3–6 | Real SMS working end to end; app offline search; seed data | App offline search; seed data |
| 6–9 | Test sets written and labelled; accuracy numbers | Slides + video from the simulator |
| 9–12 | Slides, demo video, README for judges | Submit |
| 12–15 | P2 items if P0/P1 are done | — |
| 15–17 | Buffer, submit | — |

## 7. Team split (4 people, to confirm in D10)

| Person | Work |
|---|---|
| A | SMS gateway account and number, run the server and tunnel (Claude writes the server) |
| B | Traveller app on a real phone (Claude writes starter code) |
| C | Real-world data: run `scripts/osm_gap.py`, write 15–20 host messages and 15 traveller questions in the local language with gold answers, contact 2–3 real hosts if possible (D11) |
| D | Slides and demo video |

## 8. Demo script (about 3 minutes)

1. The gap, with measured numbers from OpenStreetMap for the test region.
2. A host texts `MAKAN Warung Bu Sinaga di Garoga, nasi ikan 25rb, buka 7-21` from a basic phone. The server replies with a summary; the host replies `1`.
3. A traveller's app downloads the Garoga pack, then the phone goes into airplane mode. Searching "cheap food open now" still works and shows the listing with "confirmed today".
4. A traveller with no data texts `CARI makan Garoga` and gets 3 listings by SMS.
5. Measured accuracy, limits, and how to add a new region.

## 9. Evaluation

| What | How | Output |
|---|---|---|
| Extraction accuracy | 15–20 labelled host messages → compare each field with gold | % correct per field; % of messages needing a follow-up question |
| Traveller SMS search | 15 questions with the expected listings | % where the right listing is in the top 3 |
| Pack size and offline search | Real phone, airplane mode | KB per village; search time; works yes/no |
| Cost | SMS count per listing; LLM tokens per message | Cost per listing |

Test messages written by the team are labelled synthetic. Messages from real hosts are kept only with their consent.

## 10. Risks

| Risk | Plan |
|---|---|
| SMS replies blocked (e.g., US numbers need A2P 10DLC registration) | Test a reply in the first 30 minutes; fall back to an Android phone gateway (D4) or the simulator |
| No LLM key | Rules + follow-up questions still produce listings (D5) |
| Nobody on the team reads the test language | Ask native-speaker contacts to write and check the test messages; otherwise report results as limited |
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
