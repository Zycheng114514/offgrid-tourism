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
| D3 | Channels in the hackathon build | Decided | SMS only; no voice |
| D4 | SMS gateway for the demo | Decided | An Android phone with a SIM, running an SMS gateway app |
| D5 | LLM on the server | Decided | One interface for any model; in the demo no model runs and outputs are simulated |
| D6 | Traveller app technology | Decided | Hackathon demo: offline web app (PWA). Later: native Android app, built by Claude |
| D7 | On-device LLM for travellers | Default | Optional, last priority |
| D8 | Where the server runs for the demo | Decided | A small cloud server + Cloudflare quick tunnel; no model server |
| D9 | Repository | Decided | Public GitHub repo (from 2026-10-03); no license |
| D10 | Team roles | Decided | The team assigns roles itself |
| D11 | Contact real hosts in the test region | Decided | No; all host data is invented by Claude |
| D12 | Product name | Open | Working name `offgrid-tourism` |
| D15 | Web demo | Decided | Host side (`/host`), pipeline walkthrough (`/pipeline`), traveller side (`/app/`), landing page |
| D16 | Languages | Decided | Hosts: Indonesian, Batak Toba, English; travellers: English, Indonesian, Chinese; replies in the sender's language |
| D17 | Messages that are not reports | Decided | Classified first; chit-chat and questions never create a listing |
| D18 | Permanent live demo | Done | https://offgrid-tourism.vercel.app for the parts that keep no state; host demo and SMS simulator stay on our own server |
| D13 | Listing trust rules | Default | Host confirms by SMS; last-confirmed date; owner-only edits; phone shown only with consent |
| D14 | Which small model | Decided | Qwen3-1.7B named for later; not run in the demo (simulated outputs) |

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

## D3. Channels in the hackathon build — Decided

- **Decision:** SMS only, for hosts and travellers; the app for travellers. No voice calls and no WhatsApp in this build.
- **Trade-off we accept:** hosts who cannot type well are not served in this version; the pitch says so.
- Decided by Chris, 2026-10-03. History: SMS-only proposed by the earlier planning session; voice as a later stretch was dropped.

## D4. SMS gateway for the demo — Decided

- **Decision:** an Android phone with a SIM card runs an open-source SMS gateway app. The app forwards each incoming SMS to our server (a webhook) and sends our replies as normal SMS from that phone's number.
- **Why:** no carrier registration (unlike US numbers on Twilio, which may need A2P 10DLC registration before replies get through); normal SMS prices; the same setup can run in a village with a local SIM.
- **Needs from the team:** one Android phone with a SIM that can stay on, charged and online during the demo; a teammate installs the app.
- The simulator page is built as well, so the demo works if the phone fails.
- Decided by Chris, 2026-10-03.

## D5. LLM on the server — Decided

- **Decision:** the server talks to language models through one interface (a "port"), so any provider can be plugged in by changing settings, not code: any OpenAI-compatible server (Ollama, vLLM, llama.cpp, hosted APIs), the Anthropic API, `simulated`, or `none`.
- **In the hackathon demo no model runs** (no compute resources; Chris, 2026-10-03). The setting is `LLM_PROVIDER=simulated`: for each example message, the model output was written in advance by Claude (`models/simulated/samosir.json`). Messages that are not examples get no model output, so the server uses rules and follow-up questions only. The demo pages say this.
- The safety checks run on simulated outputs exactly as on real ones (example e8 shows an invented business name being rejected).
- Decided by Chris, 2026-10-03. History: first default was a small open model on our GPU machine; that machine became unavailable; then a model on a CPU-only cloud server; then no model.

## D6. Traveller app technology — Decided

- **Hackathon:** an offline web app (PWA) for the demo. It runs in any smartphone browser, keeps working in airplane mode after the first load, and needs no app store.
- **Later:** a native Android app. Nobody on the team builds Android apps, so Claude will write it after the hackathon. The PWA's data format (region pack) and search rules carry over unchanged.
- Decided by Chris, 2026-10-03.

## D7. On-device LLM for travellers — Default

- **Default:** optional and last. Offline search covers the common questions; a model download of hundreds of MB to several GB and the battery use are costs travellers in these places may not accept.
- If built: a small model only turns a free-text question into search filters; answers are built from listing rows.
- History: proposed by the earlier planning session.

## D8. Where the server runs for the demo — Decided

- One of our small cloud servers (1 ARM processor core, about 5 GB of free memory, no GPU) runs the app server. A Cloudflare quick tunnel gives it a public HTTPS address, which the SMS gateway app's webhook and the web app's offline mode both need. The address changes whenever the tunnel restarts. Deploy with `deploy/deploy.sh <ssh-host>`; details in `docs/RUNBOOK.md`.
- **No model server.** Our GPU machine is unavailable. A one-off try of Qwen3-1.7B on a CPU-only cloud server on 2026-10-03 took 54–73 seconds per message and returned empty output through the OpenAI-compatible JSON-schema mode; it was not debugged further and that model server was stopped.
- Decided by Chris, 2026-10-03.

## D9. Repository — Decided

- GitHub repo `Zycheng114514/offgrid-tourism`, created private on 2026-10-03 and made **public** the same day at Chris's request. No license file (all rights reserved by default).
- Before publishing, private machine names and notes about other projects were removed from the files. Earlier commits in the history still name our machines (no addresses, passwords or keys).
- History: first decided to stay private (Chris, 2026-10-03); changed to public (Chris, 2026-10-03).

## D10. Team roles — Decided

The team assigns roles among themselves. The plan lists the work items without names (PLAN.md §7).

- Decided by Chris, 2026-10-03.

## D11. Contact real hosts in the test region — Decided

- **Decision:** no contact with real businesses. All host messages, businesses and phone numbers in the demo and the test set are invented by Claude and labelled synthetic. Village names and landmarks are real.
- Decided by Chris, 2026-10-03.

## D12. Product name — Open

Working name `offgrid-tourism`. Low priority; the GitHub repo can be renamed later.

## D13. Listing trust rules — Default

Host confirms each listing by replying `1`; each listing shows the last-confirmed date; only the phone number that created a listing can edit or close it; a host's phone number is shown only with consent.

- History: proposed by the earlier planning session.

## D14. Which small model — Decided

- **Qwen3-1.7B** (Apache-2.0, about 1.4 GB at 4-bit) is the model named for a later deployment on a CPU-only server; Qwen3-4B-Instruct-2507 was the other option. Chris chose Qwen3-1.7B on 2026-10-03.
- It is not run in the demo (D5). No model comparison was run (no resources to test).
- If a model is run later, use `LLM_USER_SUFFIX=" /no_think"` to switch off Qwen3's thinking mode, and check the JSON-schema output first (see D8 for the one try).

## D15. Web demo — Decided

- `/` landing page; `/host` host side: a basic phone on the left, and on the right what the server did (each field with where it came from: rules, model (simulated), or the host's answer; rejected model values; the stored record); `/app/` traveller side: offline search over the downloaded listings, and an "Ask by SMS" tab.
- `/pipeline` pipeline walkthrough: pick an example SMS (or type one) and step through the 11 steps (SMS, gateway, route, rules, model, checks, listing fields, follow-up SMS, stored record, region pack, traveller search). Every step is computed live by the server code (`server/offgrid/trace.py`) without saving anything; the message is shown with the words each rule read highlighted; the model step can be switched off to show the rules-only path.
- Example host messages with simulated model outputs, and example traveller searches, are in `models/simulated/samosir.json`.
- Search ranking: on ties, the most recently confirmed listing comes first (server and app).
- Decided by Chris, 2026-10-03 (pipeline page requested the same day).

## D16. Languages — Decided

- **Hosts** may write in Indonesian, Batak Toba (the local language of Samosir) or English. **Travellers** may search in English, Indonesian or Chinese. The lists are in the region profile; another region lists its own languages.
- Each message's language is decided by fixed rules: the region profile has word lists per language, and the language with the most matching words wins (Chinese is matched without spaces). The same lists drive commands, category words, price units and time words, so `CARI`, `SEARCH` and `搜索` all start a search.
- Replies use the sender's language if the region has reply texts for it, otherwise a fallback set in the profile: Batak Toba → Indonesian (everyone in Samosir reads Indonesian), Chinese host messages → English. A host's language is remembered, so follow-up questions stay in it.
- The traveller app's interface can be switched between English, Indonesian and Chinese; listings show the host's own words when the reader shares the host's language, otherwise the English translation with the original below it.
- **Not checked:** the Batak Toba words were written by Claude from general knowledge and have not been checked by a native speaker.
- Decided by Chris, 2026-10-03 ("make this able to accept multiple languages").

## D17. Messages that are not reports — Decided

- Before anything is stored, each message is classified by fixed rules: command word; business report (it has a price, opening hours, rooms/people, or a business word in a message of five words or more); traveller search (a question mark, a question word, or a short message naming what or where with no price); otherwise not understood.
- Chit-chat and questions never create a listing. A question with nothing searchable gets the help text in the sender's language; a message in no recognised language gets the help text in Indonesian and English.
- Found when a test message ("what are you doing") was taken as a business report and the server asked for its category (2026-10-03).

## D18. Permanent live demo — Decided

- The submission asks for a live demo on a host such as Vercel, Replit or Lovable. Our own server's address changes whenever its tunnel restarts.
- **Vercel** hosts the parts that keep no state: landing page, pipeline walkthrough, traveller app, region pack, examples (`api/index.py` → `server/offgrid/wsgi.py`, `vercel.json`). The demo listings are loaded into memory at start-up and only read.
- The **host demo and the SMS simulator** keep conversations, so they stay on our own server. On Vercel, `/host` redirects there (address in `deploy/live_server_url.txt`), the landing page says so, and the app's "Ask by SMS" tab shows a link instead of the simulator.
- Time zones: Vercel may lack time zone data, so the region profile has a fixed UTC offset as a fallback.
- Deployed by Chris on 2026-10-03 at https://offgrid-tourism.vercel.app (Vercel Hobby plan, connected to the GitHub repo; every push to `main` redeploys). All pages, the pack and the pipeline trace were checked after the first deploy.
- Decided by Chris, 2026-10-03 ("首页、管道演示页、游客端离线应用、数据包 … use vercel").

