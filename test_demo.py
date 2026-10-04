"""Offline checks for demo adapters and interrupted-batch resume.

No real API requests. Tests use the recorded final results or an injected fake
predictor solely to check job persistence; fake outputs are never shipped as
evaluation evidence.
"""
import csv
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import demo_core as core


class DemoChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def csv_file(self, fields, rows):
        path = Path(self.tmp.name)/'input.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_exact_replay_and_changed_text(self):
        for ticket_id, expected in [('NEW001', 'High'), ('NEW003', 'Medium'),
                                    ('NEW055', 'Low'), ('NEW022', 'Escalate')]:
            result = core.predict(core.sample_text(ticket_id), core.REPLAY)
            self.assertEqual(result['final_priority'], expected)
            self.assertEqual(result['source'], 'recorded_final_test')
        with self.assertRaises(ValueError):
            core.predict('A new ticket with no recorded result.', core.REPLAY)

    def test_raw_cfpb_csv_ignores_labels(self):
        path = self.csv_file(['Complaint ID', 'Consumer complaint narrative', 'gold_priority'],
                             [{'Complaint ID': '1', 'Consumer complaint narrative': '第一行\n"第二行", fee', 'gold_priority': 'High'}])
        rows = core.upload_rows(path)
        self.assertEqual(rows, [{'ticket_id': '1', 'text': '第一行\n"第二行", fee'}])
        self.assertNotIn('gold_priority', rows[0])

    def test_generated_ids_and_invalid_uploads(self):
        rows = core.upload_rows(self.csv_file(['text'], [{'text': 'one'}, {'text': 'two'}]))
        self.assertEqual([r['ticket_id'] for r in rows], ['DEMO001', 'DEMO002'])
        for contents in [[{'ticket_id': '1', 'text': ''}],
                         [{'ticket_id': '1', 'text': 'a'}, {'ticket_id': '1', 'text': 'b'}],
                         [{'ticket_id': str(i), 'text': 'a'} for i in range(201)]]:
            with self.assertRaises(ValueError):
                core.upload_rows(self.csv_file(['ticket_id', 'text'], contents))

    def test_api_failure_retains_success_and_resume(self):
        rows = [{'ticket_id': 'A', 'text': 'first'}, {'ticket_id': 'B', 'text': 'second'}]
        job = core.prepare_job(rows, core.LIVE)
        self.addCleanup(shutil.rmtree, job)
        calls = []
        def predictor(text, **settings):
            calls.append(text)
            self.assertEqual(settings, core.SETTINGS)
            if text == 'second':
                raise RuntimeError('Simulated API failure')
            return {'raw_priority': 'Medium', 'final_priority': 'Medium', 'confidence': 0.9,
                    'reason': 'Service issue', 'status': 'ok', 'review_trigger': ''}
        with self.assertRaises(RuntimeError):
            list(core.run_job(rows, core.LIVE, job, predictor))
        saved = core.read_json(job/'predictions.json')
        self.assertEqual([r['ticket_id'] for r in saved], ['A'])
        self.assertEqual(core.prepare_job(rows, core.LIVE, str(job)), job)
        resumed = []
        def success(text, **settings):
            resumed.append(text)
            return {'raw_priority': 'High', 'final_priority': 'High', 'confidence': 0.9,
                    'reason': 'Security issue', 'status': 'ok', 'review_trigger': ''}
        list(core.run_job(rows, core.LIVE, job, success))
        self.assertEqual(resumed, ['second'])
        self.assertEqual(len(core.read_json(job/'predictions.json')), 2)
        changed = core.prepare_job(rows, core.REPLAY, str(job))
        self.addCleanup(shutil.rmtree, changed)
        self.assertNotEqual(changed, job)

    def test_final_metrics_reproduce(self):
        llm = core.router.evaluate(core.ROWS, list(core.RECORDED.values()))
        self.assertEqual(llm, core.read_json(core.ROOT/'results/llm_final_200/metrics.json'))


class EnglishUIChecks(unittest.TestCase):
    def test_english_components_and_fixed_recorded_single(self):
        import app
        import json
        import re
        ui = app.build_app()
        config = ui.config
        self.assertFalse(any(c['type'] == 'radio' for c in config['components']))
        self.assertIsNone(re.search('[\u4e00-\u9fff]', json.dumps(config, ensure_ascii=False, default=str)))
        with patch.object(core.router, 'llm_predict', side_effect=AssertionError('Single page must not call API')) as mock:
            result = app.single_route('NEW001')
            self.assertEqual(result[3]['source'], 'recorded_final_test')
            mock.assert_not_called()
        reset = app.select_sample('NEW003')
        self.assertEqual(reset[2:4], ('', ''))
        self.assertIsNone(reset[4])

    def test_csv_callback_always_live_and_resumes(self):
        import app
        payload = core.router.route_output({'raw_priority': 'Medium', 'confidence': 0.9,
                    'reason': 'Offline test output only', 'information_sufficient': True}, 0.8)
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'offline-test'}), \
                patch.object(core.router, 'llm_predict', return_value=payload) as mock:
            snapshots = list(app.batch_route(str(core.ROOT/'examples/demo_tickets.csv'), None))
            job = Path(snapshots[-1][-1])
            self.addCleanup(shutil.rmtree, job)
            self.assertEqual(mock.call_count, 4)
            for call in mock.call_args_list:
                self.assertEqual(call.kwargs, core.SETTINGS)
            records = core.read_json(job/'predictions.json')
            self.assertTrue(all(r['source'] == 'live_openrouter' for r in records))
            self.assertIn('Batch complete', snapshots[-1][0])
            list(app.batch_route(str(core.ROOT/'examples/demo_tickets.csv'), str(job)))
            self.assertEqual(mock.call_count, 4)


if __name__ == '__main__':
    unittest.main()
