"""English UI: saved single-ticket examples, live CSV batch, and fixed evals.

Single examples read recorded results. CSV batches always call the evaluated
live classifier. Neither page exposes a mode selector. The key is server-side.
"""
import os
os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
import gradio as gr
import demo_core as core

CSS = """
.gradio-container {max-width:1180px !important; margin:auto !important;}
#hero {background:#122d39; padding:30px; border-radius:18px; color:#fff; margin-bottom:16px;}
#hero h1 {margin:8px 0 12px; font-size:32px; color:white;}
#hero p {color:#d1e8e6; margin:0; font-size:15px;}
.eyebrow {color:#8fddc7; font-size:12px; letter-spacing:2px;}
.badge {padding:22px; border-radius:14px; border:1px solid #b8d6d0; background:#eef8f5; color:#173626;}
.badge strong {font-size:32px; display:block; margin:5px 0;}
.metrics {display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:14px 0;}
.metric {padding:22px; background:#eef8f5; border-radius:14px; border:1px solid #cbe3dc; color:#173626;}
.metric strong {display:block; font-size:30px; color:#134e45; margin:8px 0;}
@media(max-width:700px){.metrics{grid-template-columns:1fr;} #hero h1 {font-size:24px;}}
"""
READY = '<div class="badge">Saved example<strong>Ready to view</strong>Select a ticket and view its recorded result.</div>'


def result_card(priority, confidence):
    colors = {'High': '#a52727', 'Medium': '#9b630e', 'Low': '#24684b', 'Escalate': '#554294'}
    names = {'High': 'High priority', 'Medium': 'Medium priority', 'Low': 'Low priority', 'Escalate': 'Human review'}
    certainty = 'Unavailable' if confidence is None else f'{confidence:.0%}'
    return (f'<div class="badge" style="border-left:6px solid {colors[priority]}">'
            '<span>Saved final-test prediction · No API call</span>'
            f'<strong style="color:{colors[priority]}">{priority} · {names[priority]}</strong>'
            f'<span>Self-reported confidence: {certainty}</span></div>')


def select_sample(ticket_id):
    """Reset the previous prediction when the selected ticket changes."""
    if ticket_id not in core.EXAMPLE_IDS:
        raise gr.Error('Please select one of the provided examples.')
    return core.sample_text(ticket_id), READY, '', '', None


def single_route(ticket_id):
    """Display a stored result only; no text input or live-call option."""
    try:
        if ticket_id not in core.EXAMPLE_IDS:
            raise ValueError('Please select one of the provided examples.')
        record = core.predict(core.sample_text(ticket_id), core.REPLAY)
        trigger = record.get('review_trigger') or 'No human-review trigger'
        details = {k: v for k, v in record.items() if k != 'reason'}
        return result_card(record['final_priority'], record.get('confidence')), record['reason'], trigger, details
    except (RuntimeError, ValueError) as exc:
        raise gr.Error(str(exc)) from None


def table_rows(records):
    return [[r.get(k, '') for k in core.COLUMNS] for r in records]


def batch_route(path, previous):
    """Always use live calls; stream progress and preserve successful records."""
    try:
        rows = core.upload_rows(path)
        job = core.prepare_job(rows, core.LIVE, previous)
    except (ValueError, OSError) as exc:
        raise gr.Error(str(exc)) from None
    records = core.read_json(job/'predictions.json')
    csv_path = str(core.export_csv(job, records))
    json_path = str(job/'predictions.json')
    yield f'Live API classification · {core.summary(records, len(rows))}', table_rows(records), csv_path, json_path, str(job)
    try:
        for records in core.run_job(rows, core.LIVE, job):
            yield f'Live API classification · {core.summary(records, len(rows))}', table_rows(records), csv_path, json_path, str(job)
    except (RuntimeError, ValueError) as exc:
        yield (f'Batch paused: {str(exc)}\n{core.summary(records, len(rows))}. '
               'Resolve the issue, keep the same CSV, and click Start / Resume. Downloads contain completed tickets only.',
               table_rows(records), csv_path, json_path, str(job))
        return
    yield f'Batch complete · Live API classification · {core.summary(records, len(rows))}', table_rows(records), csv_path, json_path, str(job)


def evaluation_text():
    """Read saved final metrics; do not substitute scores from demo batches."""
    systems = core.read_json(core.ROOT/'results/baselines_final_200/metrics.json')
    systems.update(core.read_json(core.ROOT/'results/llm_final_200/metrics.json'))
    text = '| System | High recall | Macro-F1 | Accuracy | Escalate rate |\n|---|---:|---:|---:|---:|\n'
    for key, name in [('majority', 'Majority baseline'), ('keyword', 'Keyword baseline'), ('llm', 'LLM V2')]:
        m = systems[key]
        text += f"| {name} | {m['high_recall']:.2%} | {m['macro_f1']:.4f} | {m['accuracy']:.2%} | {m['escalate_rate']:.2%} |\n"
    return text


def build_app():
    with gr.Blocks(title='Bank Ticket Priority Router') as demo:
        gr.HTML('<div id="hero"><div class="eyebrow">BANK OPERATIONS · AI TRIAGE DEMO</div>'
                '<h1>Bank Ticket Priority Router</h1><p>Turn ticket narratives into priorities and reasons. '
                'Escalate when information is insufficient or confidence is below 0.80.</p></div>')
        gr.Markdown('**High · Medium · Low · Escalate to human review**')
        with gr.Tab('Single-ticket examples'):
            gr.Markdown('Explore four **saved predictions from the final evaluation**. This page makes no API calls. '
                        'Use Live CSV batch to classify new tickets.')
            with gr.Row():
                with gr.Column(scale=5):
                    sample = gr.Dropdown(choices=[('Scam loss · NEW001', 'NEW001'), ('Service dispute · NEW003', 'NEW003'),
                                                 ('General feedback · NEW055', 'NEW055'), ('Human review · NEW022', 'NEW022')],
                                         value='NEW001', label='Choose a saved example')
                    ticket = gr.Textbox(value=core.sample_text('NEW001'), label='Ticket narrative', lines=10, interactive=False)
                    route = gr.Button('View saved result', variant='primary')
                with gr.Column(scale=4):
                    card = gr.HTML(READY)
                    reason = gr.Textbox(label='Reason', lines=4, interactive=False)
                    trigger = gr.Textbox(label='Human-review trigger', interactive=False)
            with gr.Accordion('Full recorded result', open=False):
                detail = gr.JSON(label='Prediction metadata')
            sample.change(select_sample, sample, [ticket, card, reason, trigger, detail], api_name=False)
            route.click(single_route, sample, [card, reason, trigger, detail], api_name='route_single',
                        concurrency_id='inference', concurrency_limit=1)
        with gr.Tab('Live CSV batch'):
            gr.Markdown('**Real-time OpenRouter calls for every new ticket.** Upload a CSV with `ticket_id,text`, or '
                        'the CFPB columns `Complaint ID,Consumer complaint narrative`. A `text`-only file receives generated IDs. '
                        'Maximum: 200 tickets and 20 MB per batch. Completed tickets are saved and skipped on resume.')
            gr.Markdown('Configuration: **openai/gpt-4o-mini · Prompt V2 · Review threshold 0.80**. '
                        'A valid server-side OpenRouter key is required. Live results may differ from saved predictions.')
            gr.File(value=str(core.ROOT/'examples/demo_tickets.csv'), label='Download sample CSV (4 tickets)', interactive=False)
            uploaded = gr.File(label='Upload ticket CSV', file_types=['.csv'], type='filepath')
            start = gr.Button('Start / Resume', variant='primary')
            state = gr.State(None)
            progress = gr.Textbox(label='Batch progress', value='Waiting for a CSV', interactive=False)
            grid = gr.Dataframe(headers=core.COLUMNS, datatype=['str', 'str', 'str', 'number', 'str', 'str', 'str', 'str'],
                                interactive=False, label='Live batch results', wrap=True)
            with gr.Row():
                csv_file = gr.File(label='Download results CSV', interactive=False)
                json_file = gr.File(label='Download complete prediction JSON', interactive=False)
            start.click(batch_route, [uploaded, state], [progress, grid, csv_file, json_file, state],
                        api_name='route_batch', concurrency_id='inference', concurrency_limit=1)
        with gr.Tab('Final evaluation'):
            gr.Markdown('### Completed evaluation: 200 manually reviewed tickets\n60 High · 138 Medium · 2 Low. '
                        'These are saved final-test metrics; new demo batches do not change them.')
            gr.HTML('<div class="metrics"><div class="metric">High recall<strong>91.67%</strong>55 of 60 High tickets identified</div>'
                    '<div class="metric">Macro-F1<strong>0.8028</strong>Average F1 across three classes</div>'
                    '<div class="metric">Final-output accuracy<strong>94.50%</strong>189 of 200 outputs correct</div></div>')
            gr.Markdown(evaluation_text())
            gr.Markdown('**Limitations:** Five High tickets were routed Medium. Only one ticket was escalated, '
                        'and its raw prediction was correct; escalation did not intercept classification errors in this run. '
                        'Low has only two examples. Confidence is self-reported and uncalibrated.')
            gr.File(value=str(core.ROOT/'results/llm_final_200/metrics.json'), label='Download final LLM metrics', interactive=False)
        gr.Markdown('A customer-service triage prototype. Live CSV batches send ticket text to OpenRouter. '
                    'Priority suggestions support human handling decisions.')
    return demo.queue()


def launch_demo(share=False, password=None, prevent_thread_lock=False):
    password = password or os.environ.get('DEMO_PASSWORD')
    if share and not password:
        raise ValueError('Set a web login password before creating a shared demo link.')
    app = build_app()
    app.launch(share=share, auth=('hannah', password) if password else None,
               css=CSS, theme=gr.themes.Soft(primary_hue='teal', neutral_hue='slate'),
               allowed_paths=[str(core.ROOT/'examples'), str(core.ROOT/'demo_runs'),
                              str(core.ROOT/'results/llm_final_200/metrics.json')],
               blocked_paths=[str(core.ROOT/'data')],
               max_file_size='20mb', prevent_thread_lock=prevent_thread_lock, show_error=False)
    return app


if __name__ == '__main__':
    launch_demo(share=os.environ.get('DEMO_SHARE') == '1')
