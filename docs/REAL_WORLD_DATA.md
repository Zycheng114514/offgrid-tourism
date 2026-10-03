# Real-world case and data

The challenge asks for solutions built around real-world data. For us that means four things:

1. **A real place as the test example**, with public data that shows the information gap. The pipeline itself is region-independent ([DECISIONS.md](DECISIONS.md) D0); the first test region is Samosir, Indonesia (D2).
2. **Real messages in a real local language**, so accuracy is measured, not claimed.
3. **Real device and channel limits:** basic phones, 160-character SMS, offline use.
4. **No real hosts in this build** (D11): every business, message and phone number is invented and labelled synthetic; village names and landmarks are real.

Every number below is labelled **measured** (produced by a script in this repo, with the date of the data) or **not yet measured**.

## 1. The information gap in OpenStreetMap — measured

Script: `python scripts/osm_gap.py` (any region: `--area-name "<name>" --admin-level <n>`). Output: `data/real/osm/<area>/`. Data © OpenStreetMap contributors (ODbL), snapshot 2026-10-03T19:40Z.

Samosir Regency:

| Measure | Value |
|---|---|
| Food places listed (restaurant, cafe, fast food, food court) | 84 |
| Lodging places listed (hotel, guest house, hostel, motel, apartment, chalet, camp site) | 144 |
| Listed places within 3 km of Tuk Tuk, the main tourist village | 141 of 228 (62%) |
| Listed places with a phone or WhatsApp number | 17 of 228 (7%) |
| Listed places with opening hours | 12 of 228 (5%) |
| Village points with no listed food or lodging within 2 km | 76 of 132 (58%) |
| Village points with none within 5 km | 41 of 132 (31%) |

How to read this:
- Zero in OpenStreetMap means OpenStreetMap has no record. It does not mean the village has no food or lodging. That missing public record is the gap this project addresses.
- Village points are OpenStreetMap `place=village` points; they are not the official village list. 106 further `place=hamlet` points are excluded.
- The 2 km and 5 km radii are our choice. Google Maps and booking sites probably list more places in Tuk Tuk (not yet measured).

## 2. Connectivity — not yet measured

Sources to check for the test region:
- Ookla open speed-test data (tiles with mobile download speeds).
- Operator coverage maps.
- Indonesia's village census (Podes, BPS), which records mobile signal by village (availability of the downloadable table not yet checked).
- World Bank indicator: share of the population using the internet (`IT.NET.USER.ZS`).

## 3. Tourism context — sources

- World Bank Indonesia Tourism Development Project, covering Lake Toba, Lombok and Borobudur ([project document, 2018](https://documents1.worldbank.org/curated/en/839781527910281861/pdf/Indonesia-Tourism-PAD-05102018.pdf); [2025 feature on Lake Toba and Lombok](https://www.worldbank.org/en/news/feature/2025/03/19/indonesia-integrated-tourism-improving-livelihoods-for-thousands-in-lake-toba-and-lombok)).
- World Bank East Asia and Pacific [Tourism Watch](https://documents1.worldbank.org/curated/en/099449307032537375/pdf/IDU-b031e1d5-86f8-4f9c-8fb6-2a2227e417a1.pdf).
- Visitor statistics for the regency from Statistics Indonesia (BPS) (not yet collected).

## 4. Test sets — to be written

| File | Content | Who |
|---|---|---|
| `eval/host_messages.jsonl` | 15–20 host SMS in the region's language, each with the gold listing fields | Claude |
| `eval/traveller_queries.jsonl` | 15 traveller questions with the listings that should be returned | Claude |

Rules:
- Every message is labelled `"source": "synthetic"` and `"author": "claude"`.
- Real village names and landmarks; invented business names and phone numbers.
- Nobody on the team reads Indonesian (D2), so scores cover fields that can be checked without reading it: category, village, price, hours.
- The same author writes the messages and the gold answers, so the scores show the pipeline works; they do not show accuracy on real messages.

## 5. What we may and may not claim

- **May claim (measured):** the OpenStreetMap numbers above; extraction accuracy on our test set; pack size; offline search working on a real phone.
- **Must label as estimates:** effects on visitor numbers or host income. Our literature notes found no causal study showing that putting small businesses online raises their income in developing countries.
