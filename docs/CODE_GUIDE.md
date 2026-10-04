# Code and module guide

Read `PRODUCT.md` for the user-facing design and `EVALUATION.md` for scoring. This file explains how the implementation is organized so a human or AI reviewer can scan it without line-by-line comments.

| Module | Responsibility | Principal boundaries |
|---|---|---|
| `ticket_router.py` | Frozen policy prompts, baseline configuration, external model call, response validation and deterministic metrics | Receives text for inference; gold is used only by evaluation. Exact bytes are locked to the final evaluation |
| `run_final.py` | Validate frozen input hashes, run two baselines or resumable live LLM evaluation, export complete-run metrics | Fresh results default to `reruns/`; submitted `results/` is protected |
| `eval_saved.py` | Reproduce all submitted metrics offline and export confusion/error/abstention/telemetry files | Uses saved actual predictions; no new inference or model judge |
| `reproduce_selection.py` | Verify raw attachment hashes and recreate seeded candidate selection | Uses captured annotation suggestions; does not invent labels or imply blind review |
| `demo_core.py` | CSV adapters, exact recorded lookup, configuration, job persistence and CSV exports | Gold excluded from live requests; live jobs separate from formal results |
| `app.py` | English Gradio interface and callbacks | Saved single-ticket viewer, live-only CSV batch, fixed submitted evaluation |
| `test_demo.py` | Offline regression checks with stored data or explicitly injected fake predictors | Fake predictions are test fixtures only |
| Colab notebooks | Safe ZIP extraction, hidden configuration, dependency installation and entry points | No hardcoded credential or executed notebook output is included |

## Review order

1. `README.md` and `PRODUCT.md`: intended use, API boundary and metrics.
2. `data/README.md`, annotation rules and freeze record: exact inputs and label provenance.
3. `baseline_frozen.json` and prompt snapshots: fixed comparison and class boundaries.
4. `ticket_router.py`: actual evaluated inference and scoring.
5. `eval_saved.py` and saved predictions: reproduce results without network access.
6. `run_final.py`: fresh inference, checkpoint validation and complete-set reporting.
7. `demo_core.py`, `app.py` and `test_demo.py`: interface adapters and engineering checks.

## Runtime state

`results/` is submitted evidence. `data/test.csv`, `ticket_router.py` and `baseline_frozen.json` are hash-checked frozen inputs. `reruns/` and `demo_runs/` contain new runtime state and are ignored by Git. All API credentials remain in the server process environment or a hidden input; notebook outputs are cleared.

`.gitattributes` preserves exact bytes of hashed inputs and evidence when moving between Windows and Linux. Do not normalize their line endings after freezing. Changes to the interface and packaging do not alter the evaluated classifier or final set.

## Failure handling

Input errors are rejected before calls. Model refusal or invalid structured output routes to review. Network, authentication or quota errors preserve completed work and stop/pause the run, leaving unfinished tickets without fabricated predictions. Final metrics require full coverage and exactly one prediction for every labelled ticket per system. Confidence and plausible reasons do not guarantee semantic correctness; use the documented error analysis.
