# Bank Ticket Priority Router

PE6201 individual final project by CAO XIAOHAN. A bank/payment-service triage prototype that proposes **High, Medium or Low**, with a short reason and self-reported confidence, or **Escalate** for human review.

The repository includes an English demo, frozen baselines, a reviewed 200-ticket test set, real final predictions and deterministic evaluation. It does not investigate complaints or execute banking operations.

## Start here

| Need | Entry point | API key needed |
|---|---|---|
| Reproduce the submitted numbers | `python eval_saved.py` | No |
| Rerun the two frozen baselines | `python run_final.py baselines` | No |
| View saved examples and final metrics | `python app.py` | No |
| Classify a new CSV | Live CSV batch in the app | OpenRouter key |
| Make a fresh 200-ticket LLM run | `python run_final.py llm` | OpenRouter key and credit |
| Run adapter and interface checks | `python -m unittest -v test_demo` | No |

Commands run from the repository root. Evaluation uses only the Python standard library. UI requirements are installed separately.

## Local setup

Use Python 3.10 or later. Python 3.12 was used for submission verification.

```bash
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate on macOS or Linux:

```bash
source .venv/bin/activate
```

Recompute the submitted evaluation without installing UI packages or making API calls:

```bash
python eval_saved.py
```

This verifies frozen inputs and all 600 saved predictions: 200 for each baseline and 200 for the LLM. It exports the comparison, confusion matrix, errors, abstentions and recorded telemetry to `reruns/saved_analysis/`.

For the interface:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open the local URL printed in the terminal. The saved example and evaluation pages work without a key. Only live CSV classification needs one.

## Configure live classification

Obtain an OpenRouter key with available credit. Enter it into the server environment, never into source files. A hidden Python prompt works on Windows, macOS and Linux:

```bash
python -c "import os,getpass,app; os.environ['OPENROUTER_API_KEY']=getpass.getpass('OpenRouter key: ').strip(); app.launch_demo()"
```

The evaluated configuration is **OpenRouter / openai/gpt-4o-mini / prompt V2 / threshold 0.80**. Only narrative text is sent; gold labels are not. Model confidence is uncalibrated. This project sends text to an external service and requires separate privacy review before real bank use.

Optional password protection uses `DEMO_PASSWORD`. Setting `DEMO_SHARE=1` creates a temporary shared link and requires a password. The shared username is `hannah`. Colab handles hidden key and password input automatically.

## Colab setup

1. Upload `Launch_Demo_EN_Colab.ipynb` to Colab.
2. Run its upload cell and select the full repository ZIP. Either the supplied `Bank_Ticket_Router_GitHub_Repository.zip` or GitHub's **Code > Download ZIP** archive is accepted.
3. Run the dependency cell.
4. Enter the OpenRouter key into the hidden prompt, or leave it blank to view saved outputs. Set your own web password.
5. Run the launch cell, open the temporary Gradio URL, and log in as `hannah` with your password.

Keep the Colab runtime running during the demo. The temporary page closes when the runtime stops. No permanent hosting is needed to reproduce the prototype.

`Run_Final_200.ipynb` provides a separate English evaluation workflow. Offline verification requires no key. Fresh LLM evaluation is optional and consumes credit.

## Interface and CSV input

- **Single-ticket examples:** four read-only narratives and their saved final-test predictions. This page makes no API call.
- **Live CSV batch:** real calls for each unfinished ticket, downloadable CSV/JSON and checkpoint resume. There is no replay selector on this page.
- **Final evaluation:** the submitted 200-ticket metrics. Demo batches do not overwrite these results.

```csv
ticket_id,text
T001,"I did not authorize these card payments."
```

Accepted alternatives are `text` only, which generates IDs, or the CFPB columns `Complaint ID` and `Consumer complaint narrative`. Extra columns including `gold_priority` are ignored. Use CSV UTF-8; quote text containing commas or newlines. Maximum: 200 rows and 20 MB per batch. `examples/demo_tickets.csv` contains four label-free demonstration narratives.

Each successful prediction is persisted under `demo_runs/`. If an API request fails, the batch pauses without fabricating a label. In the same page session, use the same CSV and **Start / Resume** to skip completed tickets. Download results before ending the runtime; refreshing may lose the job handle.

## Fresh evaluation and separation of evidence

```bash
python run_final.py baselines
python run_final.py llm
```

The second command reads `OPENROUTER_API_KEY` from the environment. Set it with a hidden prompt when needed:

```bash
python -c "import os,getpass,run_final; os.environ['OPENROUTER_API_KEY']=getpass.getpass('OpenRouter key: ').strip(); run_final.main()" llm
```

New results go to `reruns/final_200/`, leaving submitted `results/` untouched. Rerunning the same LLM command resumes completed predictions only when the frozen configuration matches. An incomplete run does not produce final metrics. Use `--output-dir reruns/another_run` for another run. Live outputs can differ from saved predictions because upstream routing and model versions may change.

Do not refreeze baselines, revise labels or tune prompts using this final set. Changes require versioned development work and a new holdout.

## Submitted results

| System | High recall | Macro-F1 | Accuracy | Escalate rate |
|---|---:|---:|---:|---:|
| Majority | 0.00% | 0.2722 | 69.00% | 0.00% |
| Keyword | 76.67% | 0.4867 | 62.00% | 0.00% |
| LLM V2 | 91.67% | 0.8028 | 94.50% | 0.50% |

The original macro-F1 target was at least 0.80; 0.8028 narrowly reaches it. The LLM identifies 55/60 High tickets, versus keyword's 46/60. Five High tickets were missed. One abstention had a correct raw Medium label: error fraction among abstentions = 0/1. All ten raw mistakes escaped the confidence threshold. Low has only two examples, so the result does not demonstrate general Low performance or production readiness.

## Submission materials and module guide

| File or folder | Role |
|---|---|
| `data/README.md`, `data/ANNOTATION_RULES.md` | Data source, selection, splits, label provenance and priority policy |
| `data/test.csv`, `data/test_freeze.json` | Exact reviewed holdout and frozen hashes |
| `data/dev_original.csv`, `data/dev.csv`, `data/label_revisions.json` | Original development snapshot and later approved revisions |
| `data/provenance/` | Historical candidate pool, initial suggestions and selection evidence |
| `results/README.md`, `docs/EVALUATION.md` | Evaluation definitions, commands and limitations |
| `results/baselines_final_200/`, `results/llm_final_200/` | Actual submitted predictions, metrics and manifests |
| `results/analysis/` | Offline derived confusion matrix, error rows and recorded telemetry |
| `PRODUCT.md` | Persona, input, output, architecture, metric targets and reached metrics |
| `docs/CODE_GUIDE.md` | File/module responsibilities and review order |
| `ticket_router.py` | Unchanged evaluated classifier, baseline logic and deterministic metrics |
| `run_final.py` | Frozen-input validation and resumable fresh evaluation |
| `eval_saved.py` | Offline submitted-result audit and derived exports |
| `app.py`, `demo_core.py` | English UI, input adapters and batch persistence |
| `test_demo.py` | Offline adapter and UI regression checks |
| `prompts/` | V1/V2 snapshots; runtime V2 is also in `ticket_router.py` |
| `Launch_Demo_EN_Colab.ipynb`, `Run_Final_200.ipynb` | Colab demo and evaluation entry points |
| `requirements.txt` | UI dependency pins |

The classifier also contains an older development CLI. Use `run_final.py` for the fixed final V2 configuration rather than its defaults.

## Authorship and scope

This is an individual coursework project. AI assisted initial label suggestions, coding and report drafting; the author confirmed manual review of all 200 final labels. See the provenance files and limitations rather than treating the labels as blind independent annotations.

The report and face-plus-screen video are separate course deliverables. This repository supplies the code, data, evals, running instructions and product documentation.
