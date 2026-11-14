# Presets

`presets.json` lists the ready-made cases. Entries with `"kind": "csv"` read a
Giovanni time-series CSV from this folder (`file`): lines starting with `#` are
skipped, first column = time, last column = value. Drop the file here and the case
becomes `available: true` in `GET /api/presets`; no code change is needed.
Entries with `"kind": "power"` use NASA POWER for `city` + `var`.
