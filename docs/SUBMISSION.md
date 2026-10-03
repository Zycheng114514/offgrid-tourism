# Submission

Deadline: 2026-10-04 9:00 AM ET. Upload everything to **app.hack-nation.ai** and a backup copy to the organisers' **Google form** (both are required). Our notes say the World Bank track asks for the referral code `WBGSmallAIGADS`; check the form. All entries must be in English. Check the submission page for video length limits before recording.

## Checklist

| Item | Format | Status | Who | Notes |
|---|---|---|---|---|
| GitHub repo | Public link | Done | Claude | https://github.com/Zycheng114514/offgrid-tourism |
| Live demo | Stable public link | Done | Chris (Vercel), Claude | https://offgrid-tourism.vercel.app (host demo and SMS simulator on our own server, linked from it) |
| Demo video | Video | To do | Team records; Claude wrote the script | Script below |
| Tech video | Video | To do | Team records; Claude wrote the script | Script below |
| Team video | Video | To do | Team | Outline below |
| Submission text | Text fields | Draft below | Team checks | Copy into both the website and the Google form |
| Backup on Google form | Upload | To do | Team | Videos, links, text |

## Live demo

**Live demo link to submit: https://offgrid-tourism.vercel.app**

Before the Vercel deploy, the demo ran only on our own small server behind a Cloudflare quick tunnel: https://emotions-auburn-carried-divide.trycloudflare.com. It works, but the address changes whenever the server or tunnel restarts, and quick tunnels are meant for testing, so it may not survive the judging period.

The slide lists Vercel, Replit or Lovable. Options:

| Option | For | Against |
|---|---|---|
| **Vercel** | Free; permanent `*.vercel.app` address; redeploys on every push to GitHub | The demo must run without a server that keeps state: Claude changes the host demo and SMS simulator so the browser keeps the conversation and the server replays it each time. A teammate signs in to Vercel with GitHub and imports the repo (about 2 minutes) |
| Replit | Runs our server as it is | An always-on deployment needs a paid plan; the free version sleeps |
| Keep the current link | Already works | Address can change; no guarantee during judging |

Decided (D18): Vercel for the landing page, pipeline walkthrough and traveller app; the host demo and SMS simulator stay on our own server, linked from the Vercel pages.

## Submission text (draft)

**Project name:** Offgrid Tourism (working name)

**Challenge:** Tourism

**One line:** Local food and lodging businesses list themselves by SMS from any phone, in their own language; travellers search the listings offline or by SMS.

**Short description (about 100 words):**
Small guesthouses, food stalls, boat operators and guides outside tourist centres are missing from maps and booking sites, and many owners have only a basic phone. In our test region, Samosir on Lake Toba, Indonesia, 62% of the food and lodging places on OpenStreetMap are within 3 km of one tourist village, and 58% of villages have none listed nearby. Offgrid Tourism lets a host send one SMS in Indonesian, Batak Toba or English; fixed rules and a small language model turn it into a listing, the host confirms by SMS, and travellers download the region's listings (about 28 KB) to search with no connection, or ask by SMS.

**How it works:**
1. A host texts the service number from any phone. An Android phone with a local SIM, running an open-source SMS gateway app, forwards the message to our server.
2. Fixed rules decide the language and the kind of message, and read what is unambiguous: prices, opening hours, rooms, village names from the region's list.
3. A small language model reads what rules cannot: the business name, what is offered, directions, and an English translation. Every model value must be traceable to the message (names must appear in it, numbers must match, villages must be in the list) or it is dropped.
4. Anything missing is asked for by SMS, one question at a time. The host confirms the summary with "1" and decides whether their number is shown.
5. Confirmed listings go into a small file per region. The traveller web app downloads it once and searches offline; the interface is in English, Indonesian or Chinese. Travellers with signal but no data search by SMS.

**Use of AI (and what we did not do):**
AI is used only where fixed rules cannot do the job: reading free-text messages and translating them. The model is reached through one interface, so a small open model on our own server (we chose Qwen3-1.7B) or a hosted API can be plugged in by changing a setting. In this demo no model runs: we had no GPU available, and a test of Qwen3-1.7B on a 1-core CPU server took about a minute per message. For the example messages, the model's output was written in advance and is labelled as simulated everywhere it appears; any other message is handled by rules and follow-up questions. We report no accuracy numbers, because scoring outputs we wrote ourselves would measure nothing.

**Real-world data:**
Samosir Regency, Lake Toba, Indonesia, a destination in the World Bank's Indonesia Tourism Development Project. We measured the information gap on OpenStreetMap with a script that works for any region (228 food and lodging places; 62% within 3 km of Tuk Tuk; 7% with a phone number; 76 of 132 villages with none within 2 km). Village names and coordinates are real; every business, price and phone number in the demo is invented.

**Localization:**
Nothing about Samosir is in the code. Each region is a profile file: its languages and their word lists, currency and price shorthands (25rb = 25,000 rupiah), village list, reply texts and time zone. Hosts write in their own language, including the local language Batak Toba; replies fall back to Indonesian, which everyone there reads. The host side needs only a basic phone and SMS; the traveller side works with no connection; the SMS gateway uses a local SIM at local prices; the model can run on a server the community controls.

**Limits and next steps:**
No real users yet; the Batak Toba words have not been checked by a native speaker; the Android gateway is built but not yet connected to a phone; no voice reports. Next: a pilot with a tourism-village group in Samosir that seeds the first listings, a native-speaker check, real messages to evaluate a small model, and measuring whether listed businesses get more customers.

**Tech stack:** Python standard library (HTTP server, SQLite), offline web app (service worker), open-source SMS Gateway for Android, OpenAI-compatible / Anthropic model interface, JSON Schema, OpenStreetMap (Overpass API), Cloudflare tunnel.

## Demo video script (about 2 minutes)

Record the screen at 1280 px wide or more. Use the live demo link. Speak slowly; the text in quotes is the narration.

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:15 | README "The problem" table | "On Lake Toba in Indonesia, most small guesthouses and food stalls are invisible online. On OpenStreetMap, 62% of listed places sit within 3 km of one tourist village, and most villages have nothing listed at all. Many owners only have a basic phone." |
| 0:15–0:45 | `/host`: click the example "Free text, no business name", Send; click the suggested name; then `1`, `YA` | "A host texts what they offer, in their own words. Rules read the price, rooms and village; the model reads the rest. The name is missing, so the service asks for it by SMS, then sends a summary to confirm, and asks whether the number may be shown." |
| 0:45–1:00 | `/host`: New host, example "Batak Toba" | "Hosts can write in Batak Toba, the local language. The service understands it and replies in Indonesian." |
| 1:00–1:30 | `/app/`: Download listings; turn on airplane mode (or stop the network); search "cheap room Tomok"; switch to 中文 | "A traveller downloads the region's listings once, about 28 kilobytes. With no connection at all, search still works, in English, Indonesian or Chinese." |
| 1:30–1:45 | `/app/` → Ask by SMS: `SEARCH food Garoga` | "With signal but no data, the same search works by SMS." |
| 1:45–2:00 | `/pipeline`, example "The model invents a name", step 6 | "AI is used only where rules cannot do the job, and every model value is checked against the message. In this demo the model's outputs were written in advance, and all businesses are invented. The same pipeline works for any region." |

## Tech video script (about 2 minutes)

| Time | Screen | Narration |
|---|---|---|
| 0:00–0:20 | README pipeline diagram | "The host side is plain SMS: an Android phone with a local SIM runs an open-source gateway app and forwards messages to our server, a Python program with no dependencies and a SQLite database." |
| 0:20–0:50 | `/pipeline`, Play on the first example | "Each message goes through eleven steps: language and kind of message, fixed rules, the language model, checks, follow-up questions, confirmation, storage, and the region pack. This page runs the real server code without saving." |
| 0:50–1:10 | `/pipeline`, example "The model invents a name", steps 5 and 6 | "Model values are kept only if they can be traced to the message. Here the model invented a business name; the check drops it and the host is asked instead." |
| 1:10–1:30 | `regions/samosir.json` on GitHub | "Everything place-specific is in a region profile: languages and word lists, currency shorthands, villages from OpenStreetMap, reply texts. A new region is a new file." |
| 1:30–1:45 | `server/offgrid/llm.py` | "The model sits behind one interface: an OpenAI-compatible server such as Ollama with a small open model, a hosted API, simulated outputs for this demo, or none." |
| 1:45–2:00 | README "Status and limits" | "What is not done: no model runs in the demo, no real users, Batak Toba not checked by a native speaker. Next is a pilot with a tourism village in Samosir." |

## Team video outline (about 1 minute)

- Each person, 10–15 seconds: name, study or background, what they did this weekend.
- One sentence on why this problem: small local businesses in remote places are invisible to travellers, and the tools they have are a basic phone and SMS.
- One sentence on what you would do next with more time.
