# Patient Demographics & Outcome Trends — Hip Replacement Dashboard

A dashboard built on top of a cleaned New York State hip-replacement discharge
dataset. The project ships in **two forms** of the same dashboard so it can be
presented in different venues:

| Form | File | When to use |
|------|------|-------------|
| **Static HTML** | `dashboard-standalone.html` | Drop onto Netlify Drop / GitHub Pages. One file, no server. |
| **Streamlit app** | `app.py` | Deploy to Streamlit Cloud. Interactive Python backend, richer charts. |

Both forms use the **same data**, the **same 7 visualisations**, the **same
filter set**, and the **same visual language** (dark navy + orange accent,
Georgia serif headings). The Streamlit version is the deliverable for the live
demo; the HTML version is a lightweight fallback / shareable preview.

---

## 1. The dataset

**File:** `cleaned_hip_replacement_data.csv` (~9 MB, 23,080 rows)

Each row is one **inpatient discharge** from a New York State hospital for a
hip-replacement procedure in **2016**. The dataset is a cleaned subset of the
state's **SPARCS** (Statewide Planning and Research Cooperative System) release,
filtered to CCS procedure code 153 — *Hip replacement, total or partial*.

### Columns that matter for the dashboard

| Column | Meaning |
|--------|---------|
| `facility_name` | Hospital that performed the discharge (145 unique) |
| `age_group` | One of five bands: `0 to 17`, `18 to 29`, `30 to 49`, `50 to 69`, `70 or older` |
| `gender` | `f` / `m` |
| `race` | `white`, `black/african american`, `other race`, `multi-racial` |
| `ethnicity` | `not span/hispanic`, `spanish/hispanic`, `multi-ethnic`, `unknown` |
| `length_of_stay` | Integer days in hospital |
| `patient_disposition` | Where the patient went on discharge (home, skilled nursing, expired, …) — 17 unique values |
| `apr_severity_of_illness_description` | Clinical severity level: `minor`, `moderate`, `major`, `extreme` |
| `apr_risk_of_mortality` | Predicted mortality risk: same 4 levels |
| `total_charges` | What the hospital billed |
| `total_costs` | Estimated actual cost of care |

The CSV has more columns (zip, CCS diagnosis code, provider licence numbers,
etc.) — the dashboard intentionally ignores them for clarity. They're left in
the file in case we want to extend the dashboard later.

### The story the data tells

1. **Severity drives everything.** Moderate + minor cases dominate volume and
   cost; major/extreme cases are rare but expensive and long-staying.
2. **Age and mortality risk are tightly correlated.** The heatmap shows
   mortality risk concentrating in the 70+ band.
3. **Most patients go home.** About 75% of discharges are either "Home or Self
   Care" or "Home w/ Home Health Services", validating effective treatment
   pathways.
4. **Cost varies dramatically by hospital.** The top 10 hospitals by average
   total cost are clustered in NYC / Long Island and sit well above the state
   median.

---

## 2. Repository structure

```
cleaned_hip_data_processing/
├── cleaned_hip_replacement_data.csv   # raw data (23,080 rows)
│
├── README.md                          # this file
├── requirements.txt                   # python deps for streamlit
│
├── app.py                             # Streamlit dashboard (PRIMARY)
├── .streamlit/config.toml             # streamlit theme (dark + orange)
│
├── dashboard.html                     # HTML dashboard — reads data.json
├── data.json                          # compacted dataset (~977 KB)
├── dashboard-standalone.html          # HTML + inlined data (~1 MB single file)
│
├── build_data.py                      # CSV -> data.json
└── build_standalone.py                # dashboard.html + data.json -> dashboard-standalone.html
```

**Ignore at deploy time:** `.venv/`, any `__pycache__/`. Everything else is
meant to be committed.

---

## 3. How it works — data flow

```
CSV (9 MB, 23K rows)
  │
  ├──► build_data.py ──► data.json (977 KB)
  │        │                │
  │        │                └──► dashboard.html (fetch) ─► Chart.js UI
  │        │                │
  │        │                └──► build_standalone.py ─► dashboard-standalone.html
  │        │                                              (data.json inlined)
  │
  └──► app.py (pandas.read_csv, @st.cache_data) ─► Plotly UI
```

**Two separate pipelines, one source of truth.** The CSV is the only file that
changes when data updates. Both pipelines derive from it.

### Why compact the CSV to JSON for the HTML version?

Raw CSV is 9 MB — too big to sensibly bundle in an HTML page that also has to
render in a browser. `build_data.py`:

1. Keeps only the 9 columns the charts use + 3 numeric metrics (LOS, charges,
   costs).
2. Builds a **vocabulary** for each categorical column: e.g. the 145 hospital
   names become a list indexed 0-144, and every row stores the index instead of
   the full name.
3. Writes the rows as a 2-D array of small integers + floats.

Result: **977 KB** — small enough to embed directly in HTML.

### Why not do the same for Streamlit?

Streamlit runs Python on the server; it can just `pandas.read_csv` the 9 MB
file on startup and cache it with `@st.cache_data`. No need to precompute
anything.

### How filtering works

- **HTML / Chart.js:** every filter holds a `Set` of selected integer indices.
  `filterRows()` returns only rows whose `facility_name`, `age_group`, etc. are
  in the selected sets. All aggregations are recomputed on every filter change
  (roughly 23K × 9 column reads per re-render — trivially fast in modern JS).
- **Streamlit / pandas:** filters produce a boolean mask, `fdf = df[mask]`.
  Plotly redraws from the filtered DataFrame. Streamlit's reactive model means
  the whole script re-runs top-to-bottom on any filter change, but
  `@st.cache_data` keeps the CSV load out of the hot path.

---

## 4. Running locally

### Streamlit (the thing you're demoing)

```bash
# one-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run it
streamlit run app.py
# open http://localhost:8501
```

The app auto-reloads when `app.py` changes (you'll see a "Rerun" toast in the
top-right corner of the page).

### HTML (optional, for the static preview)

```bash
# two-file version — needs a local server (fetch() is blocked from file://)
python3 -m http.server 8765
# open http://localhost:8765/dashboard.html

# single-file version — open directly, no server
open dashboard-standalone.html
```

If the CSV changes:

```bash
python3 build_data.py          # regenerate data.json
python3 build_standalone.py    # regenerate dashboard-standalone.html
```

---

## 5. Deployment

### Streamlit Cloud (primary)

1. Push the repo to GitHub. Include everything *except* `.venv/`.
2. Go to **https://share.streamlit.io** → **New app**.
3. Point at the repo, main file `app.py`, branch `main`.
4. Streamlit reads `requirements.txt` automatically.
5. The app gets a URL like `hip-insights.streamlit.app`.

Add a `.gitignore`:

```
.venv/
__pycache__/
*.pyc
.DS_Store
```

### Netlify Drop (for the static HTML)

1. Go to **https://app.netlify.com/drop**.
2. Drag `dashboard-standalone.html` onto the drop zone.
3. Netlify gives you a `*.netlify.app` URL. You can rename the subdomain in
   the site settings (e.g. `hip-insights.netlify.app`).

### GitHub Pages (alternative static host)

1. Rename `dashboard-standalone.html` to `index.html`.
2. Push to a repo, enable Pages on the `main` branch.

---

## 6. File-by-file walkthrough

### `app.py` — the Streamlit dashboard

Structure, top to bottom:

1. **Imports + constants** (`PALETTE`, `SEV_RISK_COLORS`, ordered category
   lists). The colours here match what the HTML version uses — one source of
   colour truth per codebase.
2. **`load_data()`** — reads the CSV, title-cases the string columns so "f"
   becomes "Female" etc. Decorated with `@st.cache_data` so this only runs
   once per session.
3. **CSS injection (`inject_css`)** — overrides Streamlit's defaults:
   - Hides the top toolbar so our orange banner isn't clipped
   - Defines the `.kpi` card look (dark translucent panel, white 26 px value)
   - Defines `.card-title` for the Georgia-serif section headings
   - Styles `.stMultiSelect` chips orange, wraps & scrolls them so long
     selections like "all 5 age groups" don't get clipped
   - Styles the `.crosstab` table (sticky header, dashed row separators)
4. **Helpers** — `kpi()`, `card_title()`, `fmt_num()`, `fmt_money()`, and
   `apply_dark()` which sets Plotly's dark background, transparent
   `paper_bgcolor`, horizontal legend below each chart, and 11 px sans-serif.
5. **Page layout** — `st.set_page_config(layout="wide")`, then the banner.
6. **Filter row** — six `st.columns(6)` each holding a `st.multiselect` (for
   small, fixed-cardinality dims) or a `st.selectbox` (for the 145-element
   hospital list — too long to multi-select realistically).
7. **KPI row** — six cards: discharges, avg LOS, avg cost, avg charges,
   total cost, hospitals covered.
8. **Chart rows** — three `st.columns` blocks:
   - Row 1 (1-1-1): LOS by Age, Severity vs Mortality, Disposition
   - Row 2 (5-7): Heatmap, Top 10 Hospitals
   - Row 3 (1-1): Gender × Race table, Top 5 Age Groups by Cost

### `build_data.py` — CSV → JSON compactor

Reads the CSV, builds vocabularies for each categorical column, encodes every
row as `[index, index, …, los, charges, costs]`, and writes the result to
`data.json`. Run this again whenever the CSV changes.

Key design choice: **ordered dims.** `age_group`, `severity`, `risk`, and
`gender` have a natural order (e.g. `minor → moderate → major → extreme`). The
script respects that order when building the vocabulary, so the indices match
visual logic. Unordered dims (race, ethnicity, disposition, hospital) are
sorted alphabetically.

### `build_standalone.py` — inline JSON into HTML

Reads `dashboard.html`, injects a `<script>window.__DATA__ = {…json…};</script>`
right before the main script block, writes the result to
`dashboard-standalone.html`. The HTML's data loader checks for
`window.__DATA__` first, falling back to `fetch("data.json")` — so the same
HTML file works in both modes.

### `dashboard.html` — the Chart.js dashboard

Plain HTML + vanilla JS. Key pieces:

- **`<style>` block** — all the visual theme (dark radial gradients, panel
  cards, orange banner, 12-column grid).
- **`buildFilters()`** — dynamic builder that creates a checkbox list for
  small dims and a select for the hospital list. Tracks selection in a
  `SELECTED` object (`dim -> Set<number>`).
- **`filterRows()`** — scans the rows array, keeps only those whose indices
  are in every active filter's set.
- **`renderXxx()` functions** — one per chart. Each computes its own
  aggregation from the filtered rows and calls `replaceChart(id, config)`
  which destroys the old Chart.js instance and creates a new one.

Chart.js is loaded from CDN (`cdn.jsdelivr.net`), so the HTML does need
internet access the first time it loads.

### `data.json` — the compact dataset

Self-describing:

```jsonc
{
  "dims":    ["facility_name", "age_group", "gender", ...],  // column names
  "metrics": ["length_of_stay", "total_charges", "total_costs"],
  "vocab":   { "age_group": ["0 to 17", "18 to 29", ...], ... },
  "rows":    [ [idx_fac, idx_age, ..., los, charges, costs], ... ]  // 23,080 rows
}
```

### `.streamlit/config.toml` — Streamlit theme

Sets the base theme to dark, primary colour to the orange (`#ff8a1f`),
background to the deep navy (`#0b1b33`), and disables the usage-stats pinger.
`runOnSave = true` is the dev-ergonomics line that auto-reruns on file save.

### `requirements.txt`

```
streamlit>=1.32
pandas>=2.0
plotly>=5.20
```

That's it — no numpy/scipy needed because all aggregations are simple groupbys.

---

## 7. Chart-by-chart explanation

Every chart obeys the same pattern: filter the data → group → plot. Here's
what each one shows and how to read it.

| # | Title | Type | Reads |
|---|-------|------|-------|
| 1 | LOS by Age Group | Stacked bar | Avg length of stay per age band, stacked by severity. Older + sicker = longer stay. |
| 2 | Severity vs Mortality Risk | Grouped bar | Cross-tab: discharge count by severity × mortality risk. Mortality risk tracks severity almost linearly. |
| 3 | Patient Disposition | Doughnut | Top 5 dispositions + "Other". Dominated by Home / Home w/ Home Health. |
| 4 | Mortality Risk Heatmap | Heatmap (age × risk) | Where the risk mass sits. Darker colour = more discharges. Concentrated bottom-right (older + lower risk — large volume, not high danger). |
| 5 | Top 10 Hospitals by Avg Total Cost | Horizontal bar | Hospitals sorted by average cost per discharge, filtered to hospitals with ≥ 20 discharges so averages are stable. |
| 6 | Avg Total Cost by Gender & Race | Cross-tab table | Cost parity check. Values are averages in USD. Gaps here often surface equity questions. |
| 7 | Top 5 Age Groups by Avg Cost | Horizontal bar | Which age band costs most on average. Typically the extremes (0-17 and 70+) because they involve complications. |

### Common filter behaviour

- **Unselecting everything in a filter** = no rows match → KPIs show zero and
  charts show an empty state. The top of each filter row still shows the
  "ALL" chip by default.
- **Hospital filter** is a single-select (vs multi-select). The 145 options
  would swamp a multi-select UI, so we use a drop-down that starts on "All".

---

## 8. Demo talking points

A 5-7 minute walk-through you can do live.

**Opening (30 s)**
> "This is a dashboard for 23,080 hip-replacement discharges across 145 New
> York State hospitals in 2016. It's built in Streamlit, deployed on Streamlit
> Cloud. Every chart is filterable across six dimensions."

**The filters (30 s)**
> "Six filters up top — age group, gender, severity, mortality risk, race,
> hospital. They're AND-combined. As I click, every chart and KPI recomputes
> live from the filtered subset."
>
> *Demo tip: pick "Extreme" under Severity; watch the heatmap shift, costs
> climb, LOS chart grow taller.*

**The KPIs (30 s)**
> "Six headline metrics. The ones I want to point at are **average length of
> stay**, **average total cost per discharge**, and the **145 hospitals**
> count — that's our state-wide coverage."

**Chart 1: LOS by Age Group (1 min)**
> "Stacked by severity. Two things jump out: LOS climbs with age — from about
> 3 days at 0-17 to over 5 days at 70+. And within each age band, the
> severity-stacking shows that extreme + major cases are driving the stay
> length, not the volume."

**Chart 2: Severity vs Mortality Risk (1 min)**
> "This is the clinical sanity check. Mortality risk tracks severity almost
> one-to-one — if you filter to Minor severity, you'll see virtually all
> discharges have Minor mortality risk too. That's what you'd expect from a
> well-classified dataset."

**Chart 3: Patient Disposition (30 s)**
> "Where patients go after discharge. About three-quarters go home — either
> self-care or with home health services. That's actually the most important
> health-system outcome for a planned procedure like this."

**Chart 4: Mortality Heatmap (1 min)**
> "Now this is interesting — the heatmap looks 'wrong' at first. It shows
> that the biggest mass of mortality-risk discharges is in the **minor**
> category for the 30-49 and 50-69 age bands. That's volume, not danger. The
> extreme cases are the thin sliver at the top — low count, but that's where
> the mortality actually concentrates."

**Chart 5: Top 10 Hospitals (45 s)**
> "Ranked by average total cost per discharge, minimum 20 discharges per
> hospital so the averages are stable. NYC and Long Island hospitals cluster
> at the top. You could filter this by age group to see which hospitals take
> on the costliest cohorts."

**Chart 6 & 7: Gender × Race and Top Age Groups (45 s)**
> "Gender × race cost parity — check whether any group systematically costs
> more. And Top 5 Age Groups by Average Cost — usually the edges (pediatric
> and geriatric) cost the most because of complications."

**Closing (30 s)**
> "Everything's reactive, filter-driven, and sub-100 ms per update because
> pandas is doing the groupby in-process. Deploy is a push to GitHub plus a
> click on Streamlit Cloud — no container, no infra."

---

## 9. Likely Q&A

**Q: Why Streamlit and not Power BI / Tableau?**
A: Streamlit is free, open-source, Python-native, and deploys with one
click. We already had the data cleaning in Python, so keeping the whole
pipeline in one language cuts hand-offs. For this audience-size
(internal / small team), Streamlit Cloud's free tier is enough.

**Q: Why two versions (HTML + Streamlit)?**
A: The HTML version is a drop-and-share snapshot — no login, no server,
anyone can view it by opening a URL. The Streamlit version is the
interactive app with the full Python backend. We went with both so we had
a fallback and a shareable preview.

**Q: How does it scale?**
A: 23K rows is tiny. Pandas filters in single-digit milliseconds. Plotly
draws in <100 ms. The dataset could grow 100× before we'd need to move to
DuckDB or a backend query service.

**Q: How do you know the data is clean?**
A: The CSV name says it — "cleaned_hip_replacement_data.csv". The cleaning
step filtered to CCS procedure code 153 (hip replacement total/partial),
dropped rows with missing demographics, and normalised string casing. The
build script's vocabulary count is a quick integrity check — e.g. there
should always be 4 severity levels, 5 age groups, 2 genders.

**Q: What's `apr_` prefix on some columns?**
A: APR stands for **All Patient Refined** — it's 3M's severity-adjustment
system used by SPARCS. APR-DRG groups discharges by clinical
characteristics; APR severity and risk of mortality are scored on the
minor/moderate/major/extreme scale.

**Q: How would you extend this?**
A: Three directions —
1. **Year-over-year trends**: this dataset is 2016-only. Adding 2017-2023
   would enable a time-series view.
2. **Drill-down**: click a hospital bar to pivot all charts to that
   hospital only. Streamlit's `st.session_state` makes this straightforward.
3. **Cohort comparison**: two filter-sets side by side (e.g. "under 50 vs
   over 70"). Would require a minor refactor of the filter row into a
   component.

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `streamlit: command not found` | Activate the venv: `source .venv/bin/activate` |
| Port 8501 already in use | `lsof -i :8501` then `kill <pid>`, or run `streamlit run app.py --server.port 8502` |
| Charts blank, no error | Check the severity/risk/race filters — if any is empty, no rows match |
| "Could not load data.json" in the HTML version | You opened `dashboard.html` from `file://`. Use the standalone version, or run `python3 -m http.server` and open via `http://localhost:…`. |
| Streamlit Cloud build fails | Check `requirements.txt` is at the repo root and the CSV is committed (not in `.gitignore`) |

---

## 11. Credits & data provenance

- **Data:** NY State Department of Health SPARCS inpatient discharge data,
  filtered to hip replacement (CCS 153), discharge year 2016. Cleaned
  off-pipeline into `cleaned_hip_replacement_data.csv`.
- **Stack:** Streamlit · Plotly · pandas · Chart.js
- **Fonts:** Inter (body), Georgia (section titles)
- **Palette:** custom dark navy + orange with a 6-colour accent wheel for
  categorical charts.
