# Data explanation

## Source and scope

The source workflow used the CFPB Consumer Complaint Database export and user-supplied financial complaint narratives. The full approximately 640,000-row export is not included because it was not used in full for development or evaluation. The official source is [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/), accessed 4 October 2026.

The project received 190 narratives in a text attachment and 40 in a Markdown attachment. These form the documented final candidate pool of 230. This repository preserves the raw attachments under English filenames in `provenance/raw/`, normalized narratives, initial AI suggestions, review rows and the selection manifest. It does not reconstruct the upstream filtering of the entire export or original complaint IDs that were absent from the supplied narrative excerpts. NEW IDs are generated project identifiers.

CFPB says its published complaint data is available for use, analysis and building upon; it also states that the database is not a statistical sample of consumer experiences. These conditions and source cautions apply independently of project labels. See the official source above. Public availability does not guarantee that every potentially identifying detail has been removed; real bank data requires an explicit redaction and processing review.

## Files

| File | Rows or purpose | Label status |
|---|---|---|
| `dev_original.csv` | 19 development rows; 17 labelled and two blank | Original 6 High, 9 Medium, 2 Low; frozen baseline provenance |
| `dev.csv` | The same 19 development tickets | Revised 6 High, 11 Medium, no Low; two blank |
| `label_revisions.json` | Six documented development corrections | AI-assisted policy review explicitly approved by the author |
| `test.csv` | 200 final holdout tickets | Reviewed 60 High, 138 Medium, 2 Low |
| `test_freeze.json` | Exact dataset hash, IDs, classifier/baseline hashes and confirmation | Final authoritative review record |
| `provenance/source_rows_230.json` | Normalized narratives plus original attachment and line mapping | No model prediction labels |
| `provenance/ai_suggestions_230.json` | Initial policy-based suggestion, short reason, quoted evidence and review flag | Suggestions, not independent ground truth |
| `provenance/candidate_review_230.csv` | Historical candidate review worksheet | Gold was blank at this stage |
| `provenance/selection_manifest.json` | Candidate counts, exclusions, seed, selected IDs, attachment hashes | Historical pre-confirmation selection |
| `provenance/raw/source_190.txt`, `source_40.md` | Unmodified raw supplied attachments with filename mapping | Source material only |
| `../examples/demo_tickets.csv` | Four selected narratives, no labels | UI examples only; not another holdout |

The historical candidate files say review was pending and contain zero confirmed rows. That accurately describes the earlier stage. `test_freeze.json` records the later confirmation and supersedes those status fields for the selected 200 rows. Individual per-ticket review timestamps were not collected.

## Cleaning and selection

1. Preserve complaint wording. Extract text narratives and remove Markdown table boundary pipes and separator rows; collapse formatting whitespace inside cells. The captured normalized rows and their source line mapping are in `source_rows_230.json`.
2. Apply the project policy to produce AI suggestions, evidence phrases and review flags. These are stored in `ai_suggestions_230.json`. They were not obtained by calling the evaluated OpenRouter classifier.
3. Exclude rows with no provisional H/M/L label. For suspected repeated-event groups, conservatively exclude NEW121, NEW214 and NEW220, retaining earlier group members. This leaves 215 eligible rows. Exact duplicated narratives and exact narrative matches with the 19 development rows were checked and absent.
4. Within each proposed class, shuffle unflagged and flagged rows separately with seed **20261004**, then prefer unflagged candidates. Select **60 High, 138 Medium, 2 Low** and restore source order. No classifier scores are used in selection.
5. The author stated on 4 October 2026 that all selected 200 narratives had been manually reviewed and all labels agreed unchanged. Those accepted labels became `gold_priority` before final inference. The confirmation and exact frozen bytes are recorded in `test_freeze.json`.

Run `python reproduce_selection.py` to validate source hashes, reconstruct the seeded selection from captured suggestions and verify that selected IDs, texts and labels match `test.csv`. It does not regenerate annotations or claim independent human agreement.

## Leakage and limitations

Only `text` enters model requests. `gold_priority`, suggestions, evidence annotations and product metadata are excluded. The frozen baselines were not refitted after development-label revisions. The final holdout was not used for prompt tuning after evaluation.

No exact development/test text overlap does not prove there are no related complaints or events. AI-assisted labels may anchor the single reviewer. Preferring unflagged candidates and excluding ambiguous cases may make this benchmark easier than actual intake. Class proportions are selected, not natural production prevalence. With only two Low tickets, no reliable claim about broad Low-class performance is possible. US complaints also do not establish performance on Singapore banking language or workflows.
