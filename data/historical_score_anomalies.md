# Historical Dataset Archive

The previous committed database and exports were preserved before the active dataset was regenerated.

- Archive directory: `data/archive/pre_refresh_20261031T203556Z`
- Archived files: 7
- Active database: `data/supplier_scoring.db`
- Active dataset seed: `20261022`
- Active scoring run: `RUN-655a258a`

The archive contains the previous SQLite database, CSV exports, ground-truth file, malformed-case file, validation summary, source manifest, and historical anomaly report. The archive is retained for audit and comparison; it is not used for current scoring.

The active dataset passed SQLite integrity, foreign-key, expected-count, business-rule, historical score-range, and latest-run validation.
