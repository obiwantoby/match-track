# NRA Tournament Results Bulletin — format spec

Derived from sample PDFs in `docs/sample-reports/`:

| File | Event |
|------|--------|
| OPEN 22 SLOWFIRE1.pdf | Match No. 1 — .22 Slow Fire |
| OPEN 22 TIMEDFIRE1.pdf | Timed Fire |
| OPEN 22 RAPIDFIRE1.pdf | Rapid Fire |
| OPEN 22 NMC1.pdf | Match No. 2 — .22 NMC |
| OPEN 22 AGGREGATE.pdf | Match No. 5 — .22 Aggregate |
| OPEN GRAND AGG.pdf | Match No. 16 — Grand Aggregate |

## Header (every page)

```
TOURNAMENT RESULTS BULLETIN
NRA REGISTERED MATCH -- {date range or date}
{LOCATION}

MATCH NO. {n} -- {CALIBER} {EVENT NAME}
```

Footer word on samples: `OPEN` (division of tournament).

## Score display

- Primary form: `{score}.{x_count}  x`  
  Examples: `194.8 x`, `298.21 x`, `889.54 x`
- Large X counts (grand): `{score}  {x_count}  x`  
  Example: `2659  156  x`
- Sort key: **score DESC**, then **x_count DESC**, then competitor number ASC  
  (samples do not show last-target tie-break; we reserve stage reverse-order as future option)

## Sections (in order)

### 1. OPEN — PLACE AWARDS (N COMPETITORS)

Top **3** overall with labels:

| Place | Label |
|-------|--------|
| 1 | Match Winner |
| 2 | Second Place |
| 3 | Third Place |

Row: `place  competitor#  Name [suffixes]  score  x  [label]`

### 2. SPECIAL CATEGORY AWARDS

One winner each (highest score among eligible):

| Award | Eligibility |
|-------|-------------|
| High Senior | special category Senior (not Grand Senior unless also Senior) |
| High Woman | Women |
| High Civilian | division Civilian |
| High Police | division Police |
| High Service | division Service |
| High Grand Senior | Grand Senior |
| High Veteran | Veteran |

Same person may win multiple specials (e.g. Match Winner + High Civilian + High Veteran).

### 3. Class × division listings

Full ordered lists (not just top 3), with place labels on top finishers:

| Section | Classes | Division filter |
|---------|---------|-----------------|
| HIGH MASTER — POLICE/SERVICE | HM | Police **or** Service |
| HIGH MASTER — CIVILIAN | HM | Civilian |
| MASTER — POLICE/SERVICE | MA | Police or Service |
| MASTER — CIVILIAN | MA | Civilian |
| EXPERT — POLICE/SERVICE | EX | Police or Service |
| EXPERT — CIVILIAN | EX | Civilian |
| SHARPSHOOTER/MARKSMAN — ALL CATEGORIES | SS **and** MK (combined) | All divisions |

Top-place labels within a section:

- 1st: `First {Class} - {Division label}`
- 2nd: `Second ...`
- 3rd: `Third ...`
- Expert Civilian samples also label **Fourth** Expert - Civilian when present
- Sharpshooter/Marksman: First/Second/Third only

Section header includes competitor count: `(N COMPETITORS)`.

## Name suffixes (after name)

| Suffix | Meaning |
|--------|---------|
| GS | Grand Senior |
| VET | Veteran |

Order in samples: `Name GS VET` when both.

## Competitor number

3-digit style IDs (101, 212, …) — stored as `competitor_number` on shooter (match-day numbers may override later).

## Event scopes (match-track mapping)

| Bulletin event | Data source |
|----------------|-------------|
| Slow Fire | **Only** SF / SF1+SF2 — does **not** include SFNMC |
| Timed Fire | **Only** TF / TF1+TF2 — not TFNMC |
| Rapid Fire | **Only** RF / RF1+RF2 — not RFNMC |
| NMC | Separate: full NMC card total, **or** SFNMC+TFNMC+RFNMC mid-block on a 900 |
| Full total (900/600) | Entire scorecard total (distinct from NMC mid-block) |
| Caliber aggregate | Sum of all non-null totals for that caliber in the match |
| Grand aggregate | Sum of all non-null totals for the shooter in the match |

## Required shooter fields

- `name`, `competitor_number`
- `rating` (HM/MA/EX/SS/MK/UNC)
- `division` (Civilian / Police / Service)
- `special_categories` (Senior, Grand Senior, Women, Veteran — Women may combine with one other)

UNC / missing class: omitted from class sections; still eligible for OPEN place + specials.
