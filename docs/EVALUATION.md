# Evaluation explanation

## Goal and frozen comparison

The main harm is a late High ticket. Report High recall separately instead of relying only on a balanced average or accuracy. The original macro-F1 target was **at least 0.80**. The comparison also examines accuracy and abstention. No numerical High-recall or confidence-calibration target is invented after viewing results.

The evaluated systems are:

| System | Method | Frozen configuration |
|---|---|---|
| Majority | Always return Medium | Development majority before prompt work |
| Keyword | Fixed security/service terms with sentence-level negation and resolution checks | `baseline_frozen.json` |
| LLM V2 | Few-shot policy prompt with structured output and deterministic review routing | OpenRouter, `openai/gpt-4o-mini`, V2, threshold 0.80 |

All three use the same 200 gold tickets. Baseline configuration was frozen before prompt development and not changed after development-label corrections. Final baseline scores are measured on the final set, not estimated. The original classifier and frozen data/configuration files are checked against hashes before evaluation.

## Definitions

- **Accuracy:** final H/M/L outputs matching gold / all 200 tickets. Escalate does not match an H/M/L label.
- **High recall:** gold High tickets finally predicted High / all 60 gold High tickets. Escalate is a miss here.
- **High routed High or Escalate:** gold High tickets routed to either of these destinations / all gold High tickets. This safety-routing measure is distinct from correct High classification.
- **Per-class precision:** true positives / all predictions of that class. Per-class recall: true positives / all gold examples of that class. F1 is twice true positives divided by twice true positives plus false positives and false negatives.
- **Macro-F1:** unweighted mean of the High, Medium and Low F1 scores. All three are always included.
- **Escalate rate:** final Escalate outputs / all tickets.
- **Wrong raw among abstained:** abstained cases whose valid tentative H/M/L prediction was wrong / abstentions with a valid tentative H/M/L prediction. Abstentions without raw labels are counted separately and excluded from this denominator. Return null when that denominator is zero.

The human-reviewed labels provide the answer key; no LLM judge is used. Format/schema validation is an engineering check, not proof that the meaning of a classification is correct.

## Reproduce without API calls

```bash
python eval_saved.py
python reproduce_selection.py
```

The first command validates the exact submitted settings and full coverage, regenerates both baselines, recomputes each system's metrics from the saved predictions, and checks equality with saved metric files. It writes analysis to `reruns/saved_analysis/`. The checked-in `results/analysis/` contains the same derived analysis created during packaging. The second reproduces candidate selection, not model outputs.

```bash
python run_final.py baselines
```

This recomputes real baseline predictions into `reruns/final_200/baselines_final_200/` while preserving submitted evidence. No API key or third-party Python package is required for these commands.

## Fresh model evaluation

```bash
python run_final.py llm
```

Requires `OPENROUTER_API_KEY` and available credit; consumes real API tokens. Calls receive narrative text only. Gold is used afterwards by the evaluator. Each success is written immediately. An API error leaves that ticket unfinished; rerun with the same settings to resume. Configuration changes reject checkpoint reuse. Final metrics are written only after all 200 tickets complete. Use a separate `--output-dir` for another run.

Submitted directories in `results/` are protected from this runner. Never tune on the final test or edit its labels to match predictions. A genuine later correction requires a new dataset version and transparent metric changes. New live calls may differ because the model is not pinned to a dated snapshot and upstream providers can vary.

## Actual final results and critique

| System | High recall | Macro-F1 | Accuracy | Escalate rate |
|---|---:|---:|---:|---:|
| Majority | 0.00% | 0.2722 | 69.00% | 0.00% |
| Keyword | 76.67% | 0.4867 | 62.00% | 0.00% |
| LLM V2 | 91.67% | 0.8028 | 94.50% | 0.50% |

LLM High recall is 55/60, compared with 46/60 for keyword. Macro-F1 narrowly exceeds 0.80. Strict correct outputs are 189/200. The 11 final non-matches comprise ten raw classification errors and one abstention with a correct raw label. The only abstained case is NEW022: gold Medium, raw Medium, final Escalate, confidence 0.75. Wrong raw among abstained is **0/1 = 0%**. High-or-Escalate recall equals strict High recall because no High ticket escalated.

All ten raw errors had confidence 0.85–0.95 and escaped the threshold. The five High misses are NEW016, NEW056, NEW122, NEW152 and NEW211, all finally Medium. Read their saved reasons alongside the narratives: some emphasize downstream service problems and overlook security allegations. V2 also under-specifies identity theft without a stated transaction.

Low has two gold examples. Both were found, but four Medium complaints became Low, so Low precision is 2/6 = 33.33% and Low F1 is 0.5. Neither perfect Low recall on two examples nor a 0.5% escalation rate supports production claims. The chosen class mix, single-reviewer AI-assisted annotation, preference for unflagged candidates and absence of independent language-subgroup evaluation limit generalization.

Recorded final-run cost totals **USD 0.03415455**, with mean request latency **1.17419 seconds**. These describe API telemetry for this run, not total project cost or measured business ROI.

## Engineering checks

```bash
python -m unittest -v test_demo
```

Install UI dependencies first. These existing offline checks cover label exclusion, CSV validation, exact saved-example lookup, interrupted batch resume, metrics reproduction, English UI and fixed saved-single/live-batch behaviour. Injected fake predictors test persistence only; they are not the actual final evaluation results.
