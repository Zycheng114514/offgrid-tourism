# Submission

中文版：[SUBMISSION.zh.md](SUBMISSION.zh.md)

Deadline: 2026-10-04 9:00 AM ET. Upload everything to **app.hack-nation.ai** and a backup copy to the organisers' **Google form** (both are required). Our notes say the World Bank track asks for the referral code `WBGSmallAIGADS`; check the form. All entries must be in English. The submission page (seen 2026-10-03) takes one MP4 or MOV per section (team introduction, product demo, technical walkthrough), each up to 60 seconds and 1 GB, and stays open until 2026-10-04 9:15 AM ET (15-minute grace period).

## Checklist

| Item | Format | Status | Who | Notes |
|---|---|---|---|---|
| GitHub repo | Public link | Done | Claude | https://github.com/Zycheng114514/offgrid-tourism |
| Live demo | Stable public link | Done | Chris (Vercel), Claude | https://offgrid-tourism.vercel.app (host demo and SMS simulator on our own server, linked from it) |
| Demo video | Video | To do | Team records; Claude wrote the script | [demo_video_script.txt](demo_video_script.txt) |
| Tech video | Video | To do | Team records; Claude wrote the script | [tech_video_script.txt](tech_video_script.txt) |
| Team video | Video | To do | Team | Outline below |
| Team photo | JPG, PNG or WebP, up to 10 MB | To do | Team | Required before the platform lets you submit; shared with organisers and jurors |
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

Decided: Vercel for the landing page, pipeline walkthrough and traveller app; the host demo and SMS simulator stay on our own server, linked from the Vercel pages.

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
6. Travellers can also ask in their own words. Fixed rules pick the candidate listings and the model answers only from them; the answer is used only if every business it names is one of them, otherwise the reply is built from the listings. The same works by SMS. With no connection, a small model downloaded to the phone turns the question into a search.

**Use of AI (and what we did not do):**
AI is used only where fixed rules cannot do the job: reading hosts' free-text messages, translating them, and answering travellers' questions from the listings. The model is reached through one interface, so a small open model on our own server (we chose Qwen3-1.7B) or a hosted API can be plugged in by changing a setting. In this demo no model runs: we had no GPU available, and a test of Qwen3-1.7B on a 1-core CPU server took about a minute per message. For the example messages, the model's output was written in advance and is labelled as simulated everywhere it appears; any other message is handled by rules and follow-up questions. On the traveller's phone, a small model, Qwen2.5-0.5B-Instruct, runs in the browser after a one-time download (about 790 MB with a graphics chip, about 520 MB without) and only turns a question into search filters, so it cannot invent places; questions answered on the phone never leave it. In our test on a Mac laptop it took about 1 second per question with the graphics chip. We report no accuracy numbers, because scoring outputs we wrote ourselves would measure nothing.

**Real-world data:**
Samosir Regency, Lake Toba, Indonesia, a destination in the World Bank's Indonesia Tourism Development Project. We measured the information gap on OpenStreetMap with a script that works for any region (228 food and lodging places; 62% within 3 km of Tuk Tuk; 7% with a phone number; 76 of 132 villages with none within 2 km). Village names and coordinates are real; every business, price and phone number in the demo is invented.

**Localization:**
Nothing about Samosir is in the code. Each region is a profile file: its languages and their word lists, currency and price shorthands (25rb = 25,000 rupiah), village list, reply texts and time zone. Hosts write in their own language, including the local language Batak Toba; replies fall back to Indonesian, the national language. The host side needs only a basic phone and SMS; the traveller side works with no connection; the SMS gateway uses a local SIM at local prices; the model can run on a server the community controls.

**Limits and next steps:**
No real users yet; the Batak Toba words have not been checked by a native speaker; the Android gateway is built but not yet connected to a phone; no voice reports. Next: a pilot with a tourism-village group in Samosir that seeds the first listings, a native-speaker check, real messages to evaluate a small model, and measuring whether listed businesses get more customers.

**Tech stack:** Python standard library (HTTP server, SQLite), offline web app (service worker), open-source SMS Gateway for Android, OpenAI-compatible / Anthropic model interface, transformers.js with Qwen2.5-0.5B-Instruct in the browser (WebGPU or WebAssembly), JSON Schema, OpenStreetMap (Overpass API), Cloudflare tunnel.

## Demo and tech video scripts

What to click, the narration and the timing: [demo_video_script.txt](demo_video_script.txt) and [tech_video_script.txt](tech_video_script.txt).

## Team video outline (about 1 minute)

- Each person, 10–15 seconds: name, study or background, what they did this weekend.
- One sentence on why this problem: small local businesses in remote places are invisible to travellers, and the tools they have are a basic phone and SMS.
- One sentence on what you would do next with more time.
