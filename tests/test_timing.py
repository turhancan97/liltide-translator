from dataclasses import replace
import io
import json
import pickle
import time
import wave
from types import SimpleNamespace

import pytest
from rich.console import Console
from typer.testing import CliRunner

from liltide.cli import app
from liltide.exports import TranscriptExports
from liltide.provider import Caption, ProviderFailure
from liltide.session import TranslationSession
from liltide.terminal import CaptionRenderer
from liltide.timing import distribution, timing_summary


def configured_session(monkeypatch, *, now=102.4, base_ms=250, on_finalized=None):
    from liltide import session as module
    clock = SimpleNamespace(now=now)
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock.now)
    output = []
    session = TranslationSession(lambda: None, lambda: None, output.append, lambda s: None,
                                 on_finalized=on_finalized)
    session.started, session.base_ms, session.epoch = 100.0, base_ms, 'context-a'
    return session, clock, output


def test_callback_arrival_is_separate_from_handling_and_export_cost(monkeypatch):
    session, clock, output = configured_session(monkeypatch)
    provisional = Caption('0', 0, 900, 'Tekst', 'Text', False, callback_monotonic=101.2)
    session._emit(provisional)
    session._emit(replace(provisional, callback_monotonic=101.5))
    def slow_export(event):
        clock.now += 10
    session.on_finalized = slow_export
    session._emit(replace(provisional, final=True, callback_monotonic=102.0))
    final = session.finalized[0]
    assert final.start_ms == 250 and final.end_ms == 1150
    assert final.arrival_ms == 2000 and final.handled_ms == 2400
    assert final.dispatch_delay_ms == 400 and final.timing_source == 'provider_callback'
    assert final.first_provisional_arrival_ms == 1200 and final.provisional_to_final_ms == 800
    assert final.estimated_final_delay_ms == 850
    assert clock.now == 112.4  # Export/render time is not mislabeled as callback arrival.
    session._emit(replace(provisional, final=True, callback_monotonic=103.0))
    assert len(session.finalized) == 1 and len(output) == 3
    assert session.timing_summary()['estimated_final_delay']['count'] == 1


def test_handler_fallback_does_not_invent_sdk_latency(monkeypatch):
    session, _, _ = configured_session(monkeypatch)
    session._emit(Caption('0', 0, 900, 'Tekst', None, True))
    event = session.finalized[0]
    assert event.arrival_ms == event.handled_ms == 2400
    assert event.timing_source == 'session_handler'
    assert event.estimated_final_delay_ms is None and event.dispatch_delay_ms is None
    stats = session.timing_summary()
    assert stats['handler_only_captions'] == 1
    assert stats['estimated_final_delay']['count'] == 0


def test_rounding_does_not_invent_negative_local_dispatch(monkeypatch):
    session, _, _ = configured_session(monkeypatch, now=100.0008, base_ms=0)
    session._emit(Caption('0', 0, 0, 'Test', 'Test', True, callback_monotonic=100.0007))
    assert session.finalized[0].dispatch_delay_ms == 0


def test_negative_estimates_are_retained_not_clamped(monkeypatch):
    session, _, _ = configured_session(monkeypatch, base_ms=0)
    session._emit(Caption('0', 0, 5000, 'Tekst', 'Text', True, callback_monotonic=102.0))
    assert session.finalized[0].estimated_final_delay_ms == -3000
    stats = session.timing_summary()
    assert stats['negative_estimates'] == 1
    assert stats['estimated_final_delay']['median_ms'] == -3000


def test_first_observed_provisional_uses_earliest_callback_and_ignores_blanks(monkeypatch):
    session, _, _ = configured_session(monkeypatch)
    session._emit(Caption('0', 0, 900, '', '', False, callback_monotonic=100.1))
    session._emit(Caption('0', 0, 900, 'Tekst', 'Text', False, callback_monotonic=101.5))
    session._emit(Caption('0', 0, 900, 'Tekst', 'Text', False, callback_monotonic=101.2))
    session._emit(Caption('0', 0, 900, 'Tekst', 'Text', True, callback_monotonic=102))
    assert session.finalized[0].first_provisional_arrival_ms == 1200


def test_new_context_clears_unfinished_provisional_timing(monkeypatch):
    session, clock, _ = configured_session(monkeypatch)
    session._emit(Caption('0', 0, 900, 'Tekst', 'Text', False, callback_monotonic=101))
    assert session.first_provisionals
    source = SimpleNamespace(rate=16000, resume=lambda: None)
    session.source_factory = lambda: source
    session.provider_factory = lambda: SimpleNamespace(start=lambda: None)
    clock.now = 110
    session._activate()
    clock.now = 110.6
    session._emit(Caption('0', 0, 100, 'Nowy', 'New', True, callback_monotonic=110.5))
    final = session.finalized[0]
    assert final.start_ms == 10000 and final.arrival_ms == 10500
    assert final.estimated_final_delay_ms == 400
    assert final.first_provisional_arrival_ms is None and final.provisional_to_final_ms is None


def test_distribution_nearest_rank_p95_and_empty_input():
    assert distribution(range(20)) == dict(count=20, median_ms=9.5, p95_ms=18, min_ms=0, max_ms=19)
    assert distribution([]) == dict(count=0, median_ms=None, p95_ms=None, min_ms=None, max_ms=None)
    assert timing_summary([])['final_captions'] == 0


def test_summary_distinguishes_translation_and_callback_coverage():
    events = [Caption('0', 0, 100, 'Test', 'Test', True, timing_source='provider_callback', estimated_final_delay_ms=20),
              Caption('1', 100, 200, 'Test', None, True, timing_source='session_handler')]
    stats = timing_summary(events)
    assert stats['final_captions'] == 2 and stats['translated_final_captions'] == 1
    assert stats['provider_callback_captions'] == stats['handler_only_captions'] == 1
    assert stats['estimated_final_delay']['count'] == 1


def test_timed_caption_survives_process_serialization():
    event = Caption('0', 0, 100, 'Tekst', 'Text', True, callback_monotonic=123.45)
    assert pickle.loads(pickle.dumps(event)) == event
    assert '123.45' not in repr(event)  # Absolute monotonic reference is internal.


def test_timing_fields_export_without_absolute_clock(tmp_path, monkeypatch):
    path, text = tmp_path / 'session.jsonl', tmp_path / 'session.txt'
    with TranscriptExports(text, path) as sink:
        session, _, _ = configured_session(monkeypatch, on_finalized=sink.caption)
        session._emit(Caption('0', 0, 900, 'Tekst', 'Text', True, callback_monotonic=102.0))
        record = json.loads(path.read_text())
        assert record['arrival_ms'] == 2000 and record['handled_ms'] == 2400
        assert record['dispatch_delay_ms'] == 400 and record['estimated_final_delay_ms'] == 850
        assert record['first_provisional_arrival_ms'] is None
        assert record['timing_source'] == 'provider_callback'
        assert 'callback_monotonic' not in record
        assert 'Arrival: 00:00:02.000' in text.read_text()
        assert 'estimated final delay: +850 ms' in text.read_text()


def test_renderer_timing_opt_in_summary_and_negative_warning():
    output = io.StringIO()
    console = Console(file=output, force_terminal=False, width=200)
    event = Caption('0', 0, 1000, 'Tekst', 'Text', True, arrival_ms=500, handled_ms=520,
                    timing_source='provider_callback', dispatch_delay_ms=20, estimated_final_delay_ms=-500)
    with CaptionRenderer(console, 'english', show_timing=False) as renderer:
        renderer.caption(event)
    assert 'Arrived' not in output.getvalue()
    output.seek(0); output.truncate()
    with CaptionRenderer(console, 'english', show_timing=True) as renderer:
        renderer.caption(event)
        renderer.timing_summary(timing_summary([event]))
    text = output.getvalue()
    assert 'Arrived 00:00:00.500' in text and 'estimated final delay -500 ms' in text
    assert 'not benchmark latency' in text and 'negative delay estimates retained' in text
    assert 'n=1' in text and 'PL:' not in text


def test_check_audio_rejects_timing_option():
    result = CliRunner().invoke(app, ['run', '--check-audio', '--device', 'fake', '--show-timing'])
    assert result.exit_code == 1 and 'not --check-audio' in ' '.join(result.output.split())


@pytest.mark.parametrize('failure', [False, True])
def test_cli_exports_callback_timing_and_summarizes_on_success_or_error(tmp_path, monkeypatch, failure):
    from liltide import provider as module
    class FakeProvider:
        def start(self):
            pass
        def poll(self):
            now = time.monotonic()
            events = [Caption('0', 0, 0, 'Test', 'Test', False, callback_monotonic=now),
                      Caption('0', 0, 0, 'Test', 'Test', True, callback_monotonic=now)]
            if failure:
                events.append(ProviderFailure('Synthetic failure', 'unknown_cancellation'))
            return events
        def write(self, pcm):
            pass
        def finish(self):
            return iter(())
        def abort(self):
            pass
    monkeypatch.setattr(module, 'AzureProvider', lambda config: FakeProvider())
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    path, out = tmp_path / 'synthetic.wav', tmp_path / 'timing.jsonl'
    with wave.open(str(path), 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes(b'')
    result = CliRunner().invoke(app, ['run', '--source', 'file', '--file', str(path), '--confirm-f0',
        '--show-timing', '--export-jsonl', str(out)])
    assert result.exit_code == int(failure), result.output
    records = [json.loads(line) for line in out.read_text().splitlines()]
    captions = [r for r in records if r['type'] == 'segment']
    assert len(captions) == 1
    assert captions[0]['timing_source'] == 'provider_callback'
    assert captions[0]['provisional_to_final_ms'] == 0
    assert isinstance(captions[0]['arrival_ms'], int)
    output = ' '.join(result.output.split())
    assert '1 SDK callback-timed' in output and 'n=1' in output
    assert 'not benchmark latency' in output
    assert 'synthetic-not-a-real-key' not in result.output + out.read_text()


def test_arrival_clock_continues_across_recovery_without_reusing_provisional_history(monkeypatch):
    from liltide import session as module
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock.now)
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: setattr(clock, 'now', clock.now + seconds))
    class Source:
        rate = 16000
        def resume(self):
            pass
        def read(self):
            raise StopIteration
        def close(self):
            pass
    class Provider:
        def __init__(self, first):
            self.first = first
        def start(self):
            pass
        def poll(self):
            clock.now += .2
            event = Caption('0', 0, 100, 'Test', 'Test', True, callback_monotonic=clock.now)
            if self.first:
                provisional = replace(event, final=False, callback_monotonic=clock.now - .1)
                return [provisional, event, ProviderFailure('Synthetic disconnect', 'connection_failure', True)]
            return [event]
        def write(self, pcm):
            pass
        def finish(self):
            return iter(())
        def abort(self):
            pass
    providers = iter([Provider(True), Provider(False)])
    session = TranslationSession(Source, lambda: next(providers), lambda e: None, lambda s: None)
    session.run()
    first, second = session.finalized
    assert first.arrival_ms == 200 and second.arrival_ms == 1400
    assert first.provisional_to_final_ms == 100 and second.provisional_to_final_ms is None
    assert first.segment_id != second.segment_id
    assert first.estimated_final_delay_ms == second.estimated_final_delay_ms == 100
    assert session.timing_summary()['estimated_final_delay']['count'] == 2
