# offgrid-tourism

Local food and lodging information for places with weak connectivity. Hosts report by SMS from any phone, in their own language; travellers search the listings on their phone with no connection, or ask by SMS.

Built for the World Bank **Small AI for Development** hackathon, tourism track (3–4 October 2026).

> Status (2026-10-03): working demo. Server, host-side demo page and offline traveller app are built and deployed on our server s2. No language model runs in the demo: model outputs for the example messages were written in advance (see [docs/DECISIONS.md](docs/DECISIONS.md) D5). All businesses and phone numbers are invented.

## How it works

```
Host (any phone) ──SMS──► gateway ──► server: rules + LLM ──► confirmed listing (SQLite)
                                                                   │
                       region pack (JSON per village/district) ◄───┘
                                   │
Traveller app: download at a hotspot, then search offline
Traveller with signal but no data: ask by SMS, get the top 3 listings back
```

The pipeline is region-independent. Languages, currency, keywords, village names and reply texts come from a region profile in `regions/`. Samosir (Lake Toba, Indonesia) is the first test profile.

## Documents

| File | Content |
|---|---|
| [docs/PLAN.md](docs/PLAN.md) | What we build, the pipeline, scope, timeline, team split, demo script, evaluation, risks, prior work |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision log: open, default and decided items |
| [docs/REAL_WORLD_DATA.md](docs/REAL_WORLD_DATA.md) | The real-world test case, measured numbers and data sources |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Run locally, run tests, deploy to s2, connect the Android SMS gateway phone |
| [schemas/listing.schema.json](schemas/listing.schema.json) | JSON Schema for one listing |
| [regions/samosir.json](regions/samosir.json) | Region profile used for testing |
| [models/simulated/samosir.json](models/simulated/samosir.json) | Example host messages with model outputs written in advance, and example traveller searches |

## Layout

```
docs/       plan, decisions, real-world data
schemas/    JSON Schemas (listing; region pack to come)
regions/    one profile per region
server/     Python standard library only: SMS webhook, rules + LLM port, conversation, SQLite, SMS search,
            region pack export, demo pages (server/offgrid/static), tests (server/tests)
mobile/pwa/ traveller app: offline web app (PWA)
models/     prompt for the extraction task; simulated outputs for the demo
deploy/     deploy script for s2
eval/       (labelled test sets: not started)
scripts/    data scripts, e.g. osm_gap.py
data/real/  data from real sources, with provenance
data/synthetic/  invented test data, labelled as such
```

## Run it

See [docs/RUNBOOK.md](docs/RUNBOOK.md). In short: `cd server && python -m offgrid seed && LLM_PROVIDER=simulated python -m offgrid serve`, then open http://127.0.0.1:8000/.

## Try the data script

Python 3.10+, no extra packages:

```bash
python scripts/osm_gap.py --area-name Samosir --admin-level 5
```

Writes `data/real/osm/samosir/` (raw Overpass response, per-village counts, summary). Any other region works by changing the two arguments.

## Data and credits

Map data © OpenStreetMap contributors, available under the Open Database License (ODbL).
