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
| D1 | Submission cut-off | Open | To confirm on Hack-Nation |
| D2 | First test region and languages | Default | Samosir (Lake Toba, Indonesia); Indonesian |
| D3 | Channels in the hackathon build | Default | SMS only; voice is P2 |
| D4 | SMS gateway for the demo | Open | Recommended: Android phone gateway; else Twilio |
| D5 | LLM on the server | Open | Recommended: whatever key we have, default Claude Haiku 4.5; rules-only fallback |
| D6 | Traveller app technology | Open | Recommended: what the app builder knows; else a web app that works offline (PWA) |
| D7 | On-device LLM for travellers | Default | Optional, last priority |
| D8 | Where the server runs for the demo | Open | Recommended: a laptop + temporary tunnel |
| D9 | Repository | Decided / Open | Private GitHub repo created; visibility and license at submission open |
| D10 | Team roles | Open | 4-person split in PLAN.md §7 |
| D11 | Contact real hosts in the test region | Open | Recommended: try 2–3, with consent |
| D12 | Product name | Open | Working name `offgrid-tourism` |
| D13 | Listing trust rules | Default | Host confirms by SMS; last-confirmed date; owner-only edits; phone shown only with consent |

## D0. Scope of the product — Decided

The product is for any place with weak connectivity where local businesses lack online information. The pipeline must not depend on one region: everything place-specific goes in a region profile (`regions/<id>.json`). The first test region is only an example.

- Decided by Chris, 2026-10-03.

## D1. Submission cut-off — Open

An earlier planning session said about 8 hours were left. Our earlier notes record the build window as 2026-10-03 12:00 PM ET to 2026-10-04 9:00 AM ET (about 17 hours left at 4 PM ET on Oct 3). Confirm the exact time on the Hack-Nation submission page. The plan in PLAN.md §6 has a version for each.

## D2. First test region and languages — Default

- **Default:** Samosir Regency (Lake Toba, North Sumatra, Indonesia); host messages in Indonesian; Batak Toba as a stretch; traveller side in English.
- **Why:** the World Bank's Indonesia Tourism Development Project includes Lake Toba ([project document, 2018](https://documents1.worldbank.org/curated/en/839781527910281861/pdf/Indonesia-Tourism-PAD-05102018.pdf)); OpenStreetMap shows that listed food and lodging is concentrated in one area (REAL_WORLD_DATA.md); Indonesian is well supported by language models.
- **Alternatives:** a region in Laos (World Bank nature-tourism work); any region where a teammate speaks the local language.
- **Needs an answer:** does anyone on the team or among close contacts read Indonesian? Without that, nobody can check extraction quality.
- History: proposed by the earlier planning session; kept as a test example under D0.

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

## D5. LLM on the server — Open

| Option | For | Against |
|---|---|---|
| Claude Haiku 4.5 API | Fast to build; good at Indonesian and JSON output | Needs an Anthropic API key; per-call cost |
| Open small model (about 4B) on our GPU machine | Fits "small AI"; no per-call cost | Machine must stay awake and reachable; more setup time |
| Another hosted API the team already has | Uses an existing key | Depends on the key |

- **Recommendation:** code against one interface so the provider is a setting; use whichever key the team has, default Claude Haiku 4.5. Without any key, the server runs on rules plus follow-up questions. If time allows, run the same test set on a small open model and report both results.
- **Needs an answer:** which API keys does the team have?

## D6. Traveller app technology — Open

| Option | For | Against |
|---|---|---|
| Web app that works offline (PWA) | Runs on any smartphone browser, no app store; fastest to build and test | On-device LLM in a browser is harder |
| Flutter | Android and iPhone from one codebase | Needs someone who knows Flutter |
| Native Android | Best access to the phone | Android only; needs Android Studio experience |

- **Recommendation:** whatever the app builder already knows; if nobody has a preference, a PWA.

## D7. On-device LLM for travellers — Default

- **Default:** optional and last. Offline search covers the common questions; a model download of hundreds of MB to several GB and the battery use are costs travellers in these places may not accept.
- If built: a small model only turns a free-text question into search filters; answers are built from listing rows.
- History: proposed by the earlier planning session.

## D8. Where the server runs for the demo — Open

| Option | For | Against |
|---|---|---|
| A laptop + temporary tunnel (e.g., Cloudflare quick tunnel) | No account; minutes to set up | Laptop must stay awake with the lid open; URL changes on restart |
| Our GPU machine + tunnel | Can also run an open model | It suspends when idle until a sudo setting is changed |
| A cloud host | Stable URL | Account setup; free tiers may sleep and miss webhooks |

- **Recommendation:** laptop + tunnel.

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
