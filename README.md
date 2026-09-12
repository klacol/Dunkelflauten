# Dunkelflauten

Analysis of **"Dunkelflauten"** – multi-day periods of low renewable electricity
supply – in the German and European power grid, based on public data from the
[Energy-Charts API](https://api.energy-charts.info/).

> "Dunkelflaute" (literally "dark doldrums") is a German term that has also
> become common in English-language energy discussions. It describes periods
> with little wind and little solar power generation at the same time, so the
> share of renewables in the electricity mix drops sharply.

## What counts as a Dunkelflaute here?

This project defines two event categories, based on the **daily average share
of renewable energy in the load** (`ren_share_daily_avg` from Energy-Charts):

### Category A – severe Dunkelflaute (< 40 %)

- An event starts as soon as the renewable share drops below **40 %** and lasts
  for **more than one day** (i.e. at least 2 consecutive days).
- `x` = the number of consecutive days below 40 % → event label **`A{x}`**
  (e.g. `A8` = 8 consecutive days below 40 %).
- A single day below the threshold does **not** count as an event (`A1` does
  not exist), because a one-day dip can typically be buffered by batteries and
  other short-term storage.
- For the same reason, the **first day** of every event is assumed to be
  bufferable by batteries. The remaining `x - 1` days are the *critical days*
  that storage cannot cover and that require other measures (e.g. dispatchable
  power plants, imports, demand response).

### Category B – moderate Dunkelflaute (< 60 %)

- Same rules as category A, but with a **60 %** threshold → label **`B{x}`**.
- Category B is **not purely additive** to category A: a severe `A` event is
  often just the low point nested inside a wider, less severe `B` event. This
  tool detects that nesting explicitly (`contains_category_a` /
  `nested_event_ids` in the data schema) instead of just summing counts.

### Energy severity (not just day count)

Not every Dunkelflaute is equally critical: a 3-day event in December at -15 °C
(high heating load) is a bigger challenge than the same event in April at 9 °C.
A Dunkelflaute is ultimately an **energy** problem, so each event is additionally
annotated with the actual **Load** and **Residual load** (`Load - renewable
generation`, GET `/public_power`) observed during it:

- `avg_load_gw` / `avg_residual_load_gw` / `peak_residual_load_gw` – average and
  peak power, in gigawatt.
- `residual_energy_gwh` – the residual load integrated over the event's
  duration (GW × h = GWh): the energy that had to come from non-renewable
  generation, storage or imports. This lets a short, high-load winter event be
  compared fairly against a longer, low-load spring event.

## Project structure

| Path | Purpose |
| --- | --- |
| [src/dunkelflauten/models.py](src/dunkelflauten/models.py) | Data schema (`DunkelflauteEvent`) – the master-data definition of a classified event |
| [src/dunkelflauten/api_client.py](src/dunkelflauten/api_client.py) | Thin client for the Energy-Charts API |
| [src/dunkelflauten/classification.py](src/dunkelflauten/classification.py) | Detection/classification algorithm for categories A and B |
| [src/dunkelflauten/energy_analysis.py](src/dunkelflauten/energy_analysis.py) | Load / residual-load / residual-energy (GWh) metrics per event |
| [src/dunkelflauten/export.py](src/dunkelflauten/export.py) | Writes events to JSON and CSV |
| [src/dunkelflauten/cli.py](src/dunkelflauten/cli.py) | Command line script tying it all together |
| [src/dunkelflauten/config.py](src/dunkelflauten/config.py) | Loads the persisted query range from [dunkelflauten.config.json](dunkelflauten.config.json) |
| [data/\<country\>/\<year\>/](data/) | Generated JSON + CSV files, one calendar year per folder |

GitHub renders `.csv` files as browsable tables directly in the file view, so
the CSV files under `data/` can be inspected without any tooling – the JSON
files are the canonical, fully-typed version of the same data (see
[models.py](src/dunkelflauten/models.py) for the schema).

## Data source & attribution

All electricity data is fetched from the **[Energy-Charts API](https://api.energy-charts.info/)**,
a free service operated by **Fraunhofer ISE**. Many thanks to the Energy-Charts
team for maintaining this great public resource!

- Data license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) –
  attribution to *Energy-Charts.info* is required for any (re-)use of the raw
  data.
- Please respect the API's rate limits and cache/commit results instead of
  re-fetching on every run (see `data/`).

The **code** in this repository is licensed separately under the [MIT license](LICENSE).

## Usage

```powershell
# one-time setup
python -m venv .venv
.\.venv\Scripts\pip install -e .

# run via the VS Code task "Dunkelflauten: fetch & classify" (Terminal > Run Task…)
# ...or directly:
.\.venv\Scripts\python.exe -m dunkelflauten.cli
```

The query range (country, start date, optional end date) is persisted in
[dunkelflauten.config.json](dunkelflauten.config.json) so it doesn't need to be
repeated on every run:

```json
{
  "country": "de",
  "start": "2025-01-01"
}
```

If `end` is omitted, it defaults to *today*, so simply re-running the task
extends the analysed period. Command-line flags (`--country`, `--start`,
`--end`, `--outdir`, `--force`) override the config file for one-off queries,
e.g.:

```powershell
.\.venv\Scripts\python.exe -m dunkelflauten.cli --end 2025-10-21
```

The tool processes **one calendar year at a time** and writes 4 files per year
to `data/<country>/<year>/`: `dunkelflauten_A.json/.csv` and
`dunkelflauten_B.json/.csv`, plus a console summary. Complete past years (any
year before the current one) are fetched once and then left untouched on
subsequent runs – only the current, still-growing year is re-fetched every
time. Pass `--force` to re-fetch and overwrite past years too (e.g. after
Energy-Charts revises historical values).

## Validation

For Germany, 2025-01-01 to 2025-10-21, this tool currently finds 10 category-A
events (`1×A8, 1×A6, 3×A5, 2×A3, 3×A2`), very close to the manually derived
reference of 11 events (`1×A8, 1×A6, 3×A5, 2×A3, 4×A2`) that motivated this
project. Small differences are expected since Energy-Charts occasionally
revises historical values after publication.
