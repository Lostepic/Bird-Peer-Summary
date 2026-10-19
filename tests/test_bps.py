import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('bps', str(ROOT / 'bps'))
spec = importlib.util.spec_from_loader(loader.name, loader)
bps = importlib.util.module_from_spec(spec)
loader.exec_module(bps)
FIXTURE = (ROOT / 'tests/fixtures/protocols.txt').read_text()


class ParserTests(unittest.TestCase):
    def test_mixed_protocols_multichannel_and_block_boundaries(self):
        rows = bps.parse_snapshot(FIXTURE)
        self.assertEqual([r['name'] for r in rows], ['upstream_v4', 'ix_v6', 'disabled'])
        self.assertEqual(rows[0]['imported'], '1200000')
        self.assertEqual(rows[0]['exported'], '5')
        self.assertEqual(rows[0]['preferred'], '1000000')
        self.assertEqual(rows[0]['channels'], 'ipv4,ipv6')
        self.assertEqual(rows[0]['since'], '2026-10-18 12:30:00')
        self.assertEqual(rows[1]['since'], '14:03:02.123')
        self.assertIn('Connection refused', rows[1]['detail'])
        self.assertIn('retry 4.500/5', rows[1]['detail'])
        self.assertEqual(rows[2]['imported'], '0')
        self.assertEqual(bps.peer_state(rows[2]), 'down')
        self.assertIn('Administratively down', rows[2]['detail'])

    def test_custom_timestamp_and_unknown_non_bgp_protocol(self):
        text = 'Name Proto Table State Since Info\nnew Custom --- up yesterday\np BGP --- up yesterday  Established\n'
        rows = bps.parse_snapshot(text)
        self.assertEqual(rows[0]['since'], 'yesterday')
        self.assertEqual(bps.peer_state(rows[0]), 'established')

    def test_empty_table_is_valid_but_unrecognised_output_fails(self):
        self.assertEqual(bps.parse_snapshot('Name Proto Table State Since Info'), [])
        for text in ('', 'Access denied', 'Name Proto Table State Since Info\ngarbage'):
            with self.subTest(text=text), self.assertRaises(bps.BirdError):
                bps.parse_snapshot(text)


class CLITests(unittest.TestCase):
    def collect(self, argv):
        with patch.object(bps, 'resolve_birdc', return_value='birdc'), patch.object(bps, 'run', return_value=FIXTURE) as run:
            rows = bps.collect_rows(bps.parse_args(argv))
        return rows, run

    def test_single_restricted_query_with_socket_and_timeout(self):
        rows, run = self.collect(['--socket', '/run/bird6.ctl', '--timeout', '2'])
        self.assertEqual(len(rows), 3)
        run.assert_called_once_with(['birdc', '-r', '-s', '/run/bird6.ctl', 'show', 'protocols', 'all'], 2)

    def test_search_real_asn_ip_and_description(self):
        for needle in ('64501', 'AS64501', '192.0.2.1', 'TRANSIT', 'upstream v4'):
            with self.subTest(needle=needle):
                rows, _ = self.collect(['--match', needle])
                self.assertEqual([r['name'] for r in rows], ['upstream_v4'])

    def test_state_filters_and_numeric_sort(self):
        rows, _ = self.collect(['--down'])
        self.assertEqual(len(rows), 2)
        rows, _ = self.collect(['--up'])
        self.assertEqual([r['name'] for r in rows], ['upstream_v4'])
        rows, _ = self.collect(['--sort', 'imported'])
        self.assertEqual(rows[0]['imported'], '1200000')

    def test_invalid_arguments(self):
        for argv in (['--wat'], ['--watch', 'nan'], ['--watch', 'inf'], ['--timeout', '0'],
                     ['--watch', '-1'], ['--up', '--down'], ['--match']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                bps.parse_args(argv)
            self.assertEqual(exc.exception.code, 2)

    def test_help_and_version_work_without_birdc(self):
        for flag in ('--help', '--version'):
            result = subprocess.run([sys.executable, str(ROOT / 'bps'), flag], capture_output=True, text=True,
                                    env={**os.environ, 'BIRDC': '/nonexistent/birdc'})
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_json_and_empty_json(self):
        for rows in (bps.parse_snapshot(FIXTURE), []):
            output = io.StringIO()
            with patch.object(bps, 'collect_rows', return_value=rows), contextlib.redirect_stdout(output):
                self.assertEqual(bps.main(['--json']), 0)
            data = json.loads(output.getvalue())
            self.assertEqual(data['summary']['total'], len(rows))
            self.assertEqual(data['summary']['up'], 1 if rows else 0)
            if rows:
                self.assertEqual(data['peers'][0]['imported'], 1200000)

    def test_watch_redirected_json_lines_without_terminal_escape_codes(self):
        output = io.StringIO()
        with patch.object(bps, 'collect_rows', return_value=[]), patch.object(bps.time, 'sleep', side_effect=[None, KeyboardInterrupt]), contextlib.redirect_stdout(output):
            self.assertEqual(bps.main(['--json', '--watch', '.5']), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 2)
        for line in output.getvalue().splitlines():
            self.assertEqual(json.loads(line)['peers'], [])

    def test_friendly_failure_without_traceback(self):
        output = io.StringIO()
        with patch.object(bps, 'collect_rows', side_effect=bps.BirdError('socket unavailable')), contextlib.redirect_stderr(output):
            self.assertEqual(bps.main([]), 1)
        self.assertEqual(output.getvalue(), 'bps: socket unavailable\n')

    def test_timeout_and_daemon_error(self):
        with patch.object(bps.subprocess, 'run', side_effect=subprocess.TimeoutExpired('birdc', 1)):
            with self.assertRaisesRegex(bps.BirdError, 'timed out'):
                bps.run(['birdc'], 1)
        for code, stdout, stderr in ((1, '', 'Permission denied'), (0, 'syntax error', '')):
            with patch.object(bps.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, stdout, stderr)):
                with self.assertRaises(bps.BirdError):
                    bps.run(['birdc'])

    def test_explicit_missing_binary_does_not_fall_back(self):
        with patch.object(bps.shutil, 'which', return_value=None) as which:
            with self.assertRaises(bps.BirdError):
                bps.resolve_birdc('/nonexistent/birdc')
            which.assert_called_once_with('/nonexistent/birdc')


class RenderingTests(unittest.TestCase):
    def test_readable_counts_and_details_remain_available(self):
        rows = bps.parse_snapshot(FIXTURE)
        with patch.object(bps.shutil, 'get_terminal_size', return_value=os.terminal_size((180, 40))):
            clean = bps.render(rows, False, False, None)
            detailed = bps.render(rows, False, False, None, details=True)
        self.assertIn('1,200,000', clean)
        self.assertIn('3 peers  /  1 up  /  2 down', clean)
        self.assertIn('ASN', clean)
        self.assertNotIn('src 192.0.2.2', clean)
        self.assertIn('src 192.0.2.2', detailed)
        self.assertLess(bps.display_detail(rows[1]).index('Connection refused'),
                        bps.display_detail(rows[1]).index('Example exchange'))

    def test_complete_coloured_view_fits_and_plain_mode_has_no_escapes(self):
        rows = bps.parse_snapshot(FIXTURE)
        ansi = bps.re.compile(r'\x1b\[[0-9;]*m')
        for width in (20, 60, 80, 120, 180):
            with self.subTest(width=width), patch.object(bps.shutil, 'get_terminal_size', return_value=os.terminal_size((width, 40))):
                for color in (False, True):
                    output = bps.render(rows, color, False, 5)
                    self.assertTrue(all(len(ansi.sub('', line)) <= width for line in output.splitlines()))
                    if not color:
                        self.assertNotIn('\x1b', output)

    def test_tables_fit_terminal_and_since_column_is_aligned(self):
        rows = bps.parse_snapshot(FIXTURE)
        for width in (20, 60, 80, 120, 180):
            for compact in (False, True):
                with self.subTest(width=width, compact=compact), patch.object(bps.shutil, 'get_terminal_size', return_value=os.terminal_size((width, 40))):
                    table = bps.render_rows(rows, False, compact)
                    self.assertTrue(all(len(line) <= width for line in table.splitlines()))
                    self.assertNotIn('\x1b', table)
                    if width == 180 and not compact:
                        lines = table.splitlines()
                        start = lines[0].index('SINCE')
                        self.assertTrue(lines[2][start:].startswith('2026-10-18'))
                        self.assertTrue(lines[3][start:].startswith('14:03:02'))

    def test_daemon_control_characters_are_not_rendered(self):
        rows = bps.parse_snapshot(FIXTURE)
        rows[0]['detail'] = '\x1b[2J\tInjected'
        rows[0]['description'] = '\x1b[2J\tInjected'
        for details in (False, True):
            self.assertNotIn('\x1b', bps.render_rows(rows, False, True, details))


if __name__ == '__main__':
    unittest.main()
