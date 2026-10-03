# Video scripts

中文版：[VIDEO_SCRIPTS.zh.md](VIDEO_SCRIPTS.zh.md)

Two videos: the **demo video** shows what the product does; the **tech video** explains how the approach works. The narration is written to be clear first; the length follows from it.

**Length** (words counted; time = words ÷ speaking speed + time waiting for the screen):

| Video | Words | At 140 words/min | At 120 words/min (slower) |
|---|---|---|---|
| Demo | 191 | about 1:46 | about 2:00 |
| Tech | 221 | about 1:51 | about 2:06 |

Check the submission page for a length limit before recording.

## Before recording

- Chrome, window about 1280 px wide, zoom 100–110%, bookmarks bar hidden, other tabs closed.
- Open these tabs in order:
  1. https://github.com/Zycheng114514/offgrid-tourism#the-problem (README, the problem table)
  2. https://offgrid-tourism.vercel.app/host (forwards to our own server). Click **New host** so the conversation is empty.
  3. https://offgrid-tourism.vercel.app/app/
  4. https://emotions-auburn-carried-divide.trycloudflare.com/app/ , switched to the **Ask by SMS** tab (the SMS simulator runs on our own server only)
  5. https://offgrid-tourism.vercel.app/pipeline
- Going offline: turn off Wi-Fi (cleaner than Chrome DevTools → Network → Offline).
- Recording on a Mac: Shift-Command-5 → record the screen or a selected area → Options → choose the microphone. Or record the screen first and add the voice afterwards.
- Check right before recording that tabs 2 and 4 load; our own server's address can change if it restarts.

## Demo video

| # | Screen | Narration | Time |
|---|---|---|---|
| 1 | Tab 1: stay on the "The problem" table | "In Samosir, on Lake Toba in Indonesia, small guesthouses and food stalls are hard to find online. On OpenStreetMap, 58 percent of villages have no food or lodging listed nearby, and only 7 percent of listings have a phone number. So we built a system that works with a basic phone and a weak connection." | 0:24–0:28 |
| 2 | Tab 2: click the example "Free text, no business name…", **Send**; wait for the question; click the suggested reply "Homestay Pelabuhan Indah"; wait for the summary; click **1**, then **YA**. The right panel shows where each field came from | "A host sends one SMS, in their own words. The system reads the price, the rooms and the village, and asks by SMS for anything missing. Here, it asks for the business name. The host confirms with 1, and the listing goes live." | 0:26–0:30 |
| 3 | Tab 2: **New host**; example "Batak Toba (local language)…", **Send**; the reply is in Indonesian | "It also understands Batak Toba, the local language, and replies in Indonesian." | 0:08–0:09 |
| 4 | Tab 3: **Download listings** (shows 20 listings, 28 KB); turn off Wi-Fi; type `cheap room Tomok`; switch the language menu to 中文; click the example `便宜 住宿` | "A traveller downloads the region's listings once. That's 28 kilobytes. Then, with no connection at all, they can still search for food, rooms, boats or guides, in English, Indonesian or Chinese." | 0:21–0:24 |
| 5 | Turn Wi-Fi back on. Tab 4: click the example `SEARCH food Garoga`; wait for the reply | "With phone signal but no data, the same search works by SMS." | 0:08–0:09 |
| 6 | Tab 5: click the example "The model invents a name…", then step 6 "Checks against the message"; stay on the table with "rejected" | "AI is used only where rules can't do the job, and everything the model gives is checked against the original message. In this demo, the model's outputs were prepared in advance, and all the businesses are made up." | 0:18–0:21 |

## Tech video

| # | Screen | Narration | Time |
|---|---|---|---|
| 1 | Tab 1: scroll to "How the pipeline works"; stay on the diagram and table | "Here's how it works. A host's SMS reaches an Android phone with a local SIM, which forwards it to our server. The server is plain Python with a small database. Travellers use an offline web app." | 0:17–0:20 |
| 2 | Tab 5: example "Keyword format: everything in one SMS"; click step 4 "Fixed rules read the clear parts". The words the rules read are highlighted in the message | "Every message goes through the same steps. First, fixed rules detect the language and read what is clear: prices like 25 rb, opening hours, rooms, and village names. The highlighted words are what the rules found." | 0:18–0:21 |
| 3 | Tab 5: example "The model invents a name…"; step 5 (model output), then step 6 (checks: "rejected") | "Then a small language model reads what rules can't: the business name, the offer, and an English translation. Every value it gives must appear in the original message. Here it made up a name, so the system rejects it and asks the host instead." | 0:23–0:26 |
| 4 | New tab: https://github.com/Zycheng114514/offgrid-tourism/blob/main/regions/samosir.json , scroll through "languages" and "words". Back to tab 5: type `搜索 便宜 住宿 Tomok`, **Run the pipeline**; step 3 shows "Chinese" | "Nothing is hard-coded for Samosir. Each region is one settings file: its languages, words, currency and villages. That's how one system handles Indonesian, Batak Toba, English and Chinese, and how a new region is added." | 0:18–0:21 |
| 5 | New tab: https://github.com/Zycheng114514/offgrid-tourism/blob/main/server/offgrid/llm.py , stay on the description at the top (openai_compatible, anthropic, simulated, none) | "The model plugs in through one interface: a small open model on our own server, a hosted one, or none. In this demo no model runs. Its outputs for the examples were written in advance." | 0:17–0:20 |
| 6 | Tab 3: one offline search; then tab 1, README "Status and limits" | "The traveller app works offline after one download, and the demo is live on Vercel. Next, we want to pilot it with a tourism village in Samosir, and test a small model on real messages." | 0:17–0:20 |
