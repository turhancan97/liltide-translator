import json

import numpy as np
import pytest
from typer.testing import CliRunner

from liltide.audio import AudioError
from liltide.cli import app
from liltide.events import Gap
from liltide.exports import TranscriptExports
from liltide.provider import Caption, ProviderError, ProviderFailure
from liltide.session import TranslationSession


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []
        self.before_sleep = lambda: None
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.before_sleep()
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    from liltide import session
    clock = Clock()
    monkeypatch.setattr(session.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(session.time, "sleep", clock.sleep)
    return clock


def final():
    return Caption("0", 0, 100, "Cześć", "Hello", True)


def transient():
    return ProviderError("Synthetic network failure", reason="connection_failure", retryable=True)


class Source:
    rate = 16000
    def __init__(self, clock, value=.1):
        self.clock = clock
        self.value = value
        self.closed = False
        self.reads = 0
        self.resumes = 0
    def read(self):
        assert not self.closed
        self.reads += 1
        self.clock.now += .2
        if self.reads > 1:
            raise StopIteration
        return np.full((1600, 1), self.value, dtype=np.float32)
    def resume(self):
        self.resumes += 1
    def close(self):
        self.closed = True


class Provider:
    def __init__(self, polls=(), *, start_error=None, finish_error=None):
        self.polls = list(polls)
        self.start_error = start_error
        self.finish_error = finish_error
        self.aborted = False
        self.writes = []
    def start(self):
        if self.start_error:
            raise self.start_error
    def poll(self):
        result = self.polls.pop(0) if self.polls else []
        if isinstance(result, Exception):
            raise result
        return result
    def write(self, pcm):
        if pcm:
            self.writes.append(pcm)
    def finish(self):
        yield from ()
        if self.finish_error:
            raise self.finish_error
    def abort(self):
        self.aborted = True


def factories(clock, providers):
    sources, opened = [], []
    def source_factory():
        source = Source(clock, .1 if not sources else .5)
        sources.append(source)
        return source
    def provider_factory():
        result = providers[len(opened)]
        opened.append(result)
        return result
    return source_factory, provider_factory, sources, opened


def test_reconnect_exports_gap_and_uses_fresh_audio_and_segment_ids(clock, tmp_path):
    providers = [Provider([[final()], [ProviderFailure("Disconnected", "connection_failure", True)]]),
                 Provider([[final()]])]
    sf, pf, sources, opened = factories(clock, providers)
    clock.before_sleep = lambda: all_closed(sources)
    path, text = tmp_path / "session.jsonl", tmp_path / "session.txt"
    statuses = []
    with TranscriptExports(text, path) as sink:
        session = TranslationSession(sf, pf, lambda e: None, statuses.append,
                                     on_finalized=sink.caption, on_gap=sink.gap)
        session.run()
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r['type'] for r in records] == ['segment', 'gap', 'gap', 'segment']
    assert len({r['session_id'] for r in records}) == 1
    assert records[0]['segment_id'] != records[3]['segment_id']
    assert records[1]['start_ms'] == records[0]['end_ms']
    assert records[1]['end_ms'] == records[2]['start_ms']
    assert records[2]['end_ms'] == records[3]['start_ms']
    assert records[1]['reason'] == 'connection_failure'
    assert records[2]['end_ms'] - records[1]['start_ms'] >= 1000
    assert '[gap]' in text.read_text() and 'audio may be missing or unfinalized' in text.read_text()
    assert session.retries == 1 and len(session.finalized) == 2
    assert len(opened) == len(sources) == 2
    assert all(s.closed for s in sources) and all(p.aborted for p in providers)
    assert sources[0].reads == 1  # Stale queued audio is not read after failure.
    assert np.frombuffer(providers[0].writes[0], '<i2')[0] == pytest.approx(3277, abs=1)
    assert np.frombuffer(providers[1].writes[0], '<i2')[0] == 16384


def all_closed(sources):
    assert all(s.closed for s in sources), 'Live capture must be stopped throughout backoff'


def test_three_attempts_use_1_2_4_backoff_and_then_stop(clock):
    providers = [Provider([transient()])] + [Provider(start_error=transient()) for _ in range(3)]
    sf, pf, sources, opened = factories(clock, providers)
    clock.before_sleep = lambda: all_closed(sources)
    statuses, gaps = [], []
    session = TranslationSession(sf, pf, lambda e: None, statuses.append, on_gap=gaps.append)
    with pytest.raises(ProviderError, match='Reconnect limit'):
        session.run()
    assert session.retries == 3 and len(opened) == 4
    assert clock.now == pytest.approx(7)
    assert len(gaps) == 2 and gaps[0].start_ms == 0 and gaps[-1].end_ms == 7000
    assert all(p.aborted for p in providers) and all(s.closed for s in sources)
    assert any('1/3 in 1 seconds' in s for s in statuses)
    assert any('2/3 in 2 seconds' in s for s in statuses)
    assert any('3/3 in 4 seconds' in s for s in statuses)


@pytest.mark.parametrize('reason', ['authentication_failure', 'rate_or_quota_limit', 'access_denied', 'unknown_cancellation'])
@pytest.mark.parametrize('startup', [False, True])
def test_fatal_failure_never_retries(clock, reason, startup):
    error = ProviderError('Synthetic fatal error', reason=reason)
    provider = Provider(start_error=error) if startup else Provider([error])
    sf, pf, sources, opened = factories(clock, [provider])
    gaps = []
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None, on_gap=gaps.append)
    with pytest.raises(ProviderError, match='fatal'):
        session.run()
    assert session.retries == 0 and len(opened) == 1 and not clock.sleeps
    assert len(gaps) == 1 and gaps[0].reason == reason
    assert provider.aborted and sources[0].closed


def test_fatal_error_during_retry_stops_remaining_attempts(clock):
    providers = [Provider([transient()]), Provider(start_error=ProviderError('Invalid key', reason='authentication_failure'))]
    sf, pf, sources, opened = factories(clock, providers)
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None)
    with pytest.raises(ProviderError, match='Invalid key'):
        session.run()
    assert session.retries == 1 and len(opened) == 2
    assert clock.now == pytest.approx(1)


def test_retry_budget_does_not_reset_after_successful_reconnections(clock):
    providers = [Provider([[final()], transient()]) for _ in range(4)]
    sf, pf, sources, opened = factories(clock, providers)
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None)
    with pytest.raises(ProviderError, match='Reconnect limit'):
        session.run()
    assert session.retries == 3 and len(opened) == 4
    assert len(session.finalized) == 4
    assert len(session.gaps) >= 4


def test_ctrl_c_during_backoff_closes_gap_without_new_attempt(clock, tmp_path):
    providers = [Provider([[final()], transient()])]
    sf, pf, sources, opened = factories(clock, providers)
    def interrupt():
        raise KeyboardInterrupt
    clock.before_sleep = interrupt
    path = tmp_path / 'session.jsonl'
    with TranscriptExports(jsonl_path=path) as sink:
        session = TranslationSession(sf, pf, lambda e: None, lambda s: None,
                                     on_finalized=sink.caption, on_gap=sink.gap)
        session.run()
    assert len(opened) == 1 and session.retries == 0
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r['type'] for r in records] == ['segment', 'gap']
    assert providers[0].aborted and sources[0].closed


def test_duration_expires_during_backoff(clock):
    sf, pf, sources, opened = factories(clock, [Provider([transient()])])
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None, duration=.2)
    session.run()
    assert len(opened) == 1 and session.retries == 0
    assert session.gaps[-1].end_ms >= 200


def test_initial_startup_recovers_without_starting_old_capture(clock):
    providers = [Provider(start_error=transient()), Provider([[final()]])]
    sf, pf, sources, opened = factories(clock, providers)
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None)
    session.run()
    assert sources[0].reads == 0 and sources[0].closed
    assert len(opened) == 2 and session.retries == 1
    assert session.gaps[0].start_ms == 0 and session.gaps[-1].end_ms == 1000


def test_file_recovery_keeps_cursor_and_does_not_replay_consumed_audio(clock):
    source = Source(clock)
    providers = [Provider([[final()], transient()]), Provider([[final()]])]
    opened = []
    def pf():
        p = providers[len(opened)]
        opened.append(p)
        return p
    session = TranslationSession(lambda: source, pf, lambda e: None, lambda s: None, file_input=True)
    session.run()
    assert source.reads == 2 and source.resumes == 2 and source.closed
    assert providers[0].writes and not providers[1].writes
    assert session.retries == 1


def test_gap_export_failure_never_retries_persistence(clock):
    providers = [Provider([transient()]), Provider()]
    sf, pf, sources, opened = factories(clock, providers)
    calls = []
    def failed_export(gap):
        calls.append(gap)
        raise AudioError('Synthetic export write failure')
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None, on_gap=failed_export)
    with pytest.raises(AudioError, match='export write failure'):
        session.run()
    assert len(calls) == 1 and len(opened) == 1
    assert all(p.aborted for p in opened) and all(s.closed for s in sources)


def test_pause_drain_connection_failure_does_not_auto_resume(clock):
    providers = [Provider([[final()]], finish_error=transient()), Provider([[final()]])]
    sf, pf, sources, opened = factories(clock, providers)
    keys = iter([None, 'pause', None, 'pause', None])
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None, lambda: next(keys, None))
    session.run()
    assert len(opened) == 2 and session.retries == 0 and len(session.gaps) == 1
    assert all(p.aborted for p in providers) and all(s.closed for s in sources)


def test_gap_record_does_not_contain_captions_or_credentials(tmp_path):
    path = tmp_path / 'session.jsonl'
    with TranscriptExports(jsonl_path=path) as sink:
        sink.gap(Gap(100, 500, 'connection_failure'))
    record = json.loads(path.read_text())
    assert set(record) == {'type', 'session_id', 'start_ms', 'end_ms', 'reason'}
    assert record['type'] == 'gap' and record['reason'] == 'connection_failure'


def test_final_in_failure_batch_is_saved_before_recovery(clock):
    providers = [Provider([[final(), ProviderFailure('Disconnected', 'connection_failure', True)]]), Provider()]
    sf, pf, sources, opened = factories(clock, providers)
    seen = []
    session = TranslationSession(sf, pf, lambda e: None, lambda s: None, on_finalized=seen.append)
    session.run()
    assert len(seen) == 1 and session.retries == 1
    assert sources[0].reads == 0 and providers[0].aborted


def test_gap_checkpoint_exists_on_disk_before_retry_wait(clock, tmp_path):
    sf, pf, sources, opened = factories(clock, [Provider([transient()]), Provider()])
    path = tmp_path / 'session.jsonl'
    checked = []
    def before_sleep():
        record = json.loads(path.read_text().splitlines()[0])
        assert record['type'] == 'gap'
        checked.append(True)
    clock.before_sleep = before_sleep
    with TranscriptExports(jsonl_path=path) as sink:
        TranslationSession(sf, pf, lambda e: None, lambda s: None, on_gap=sink.gap).run()
    assert checked


def test_source_failure_stops_without_reconnecting_and_marks_gap(clock):
    provider = Provider([[final()]])
    source = Source(clock)
    def read():
        raise AudioError('Synthetic removed device')
    source.read = read
    gaps = []
    session = TranslationSession(lambda: source, lambda: provider, lambda e: None, lambda s: None, on_gap=gaps.append)
    with pytest.raises(AudioError, match='removed device'):
        session.run()
    assert session.retries == 0 and provider.aborted and source.closed
    assert gaps[0].reason == 'source_failure'


def test_eof_drain_failure_records_gap_but_does_not_restart(clock):
    provider = Provider(finish_error=transient())
    source = Source(clock)
    session = TranslationSession(lambda: source, lambda: provider, lambda e: None, lambda s: None)
    with pytest.raises(ProviderError):
        session.run()
    assert session.retries == 0 and len(session.gaps) == 1
    assert source.closed and provider.aborted


def test_cli_recovery_keeps_export_session_and_same_cloud_config(clock, tmp_path, monkeypatch):
    from liltide import provider as provider_module, sources as sources_module
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    source = Source(clock)
    providers = [Provider([[final()], transient()]), Provider([[final()]])]
    configs = []
    def factory(config):
        configs.append(config)
        return providers[len(configs) - 1]
    monkeypatch.setattr(provider_module, 'AzureProvider', factory)
    monkeypatch.setattr(sources_module, 'WaveSource', lambda path: source)
    text, data = tmp_path / 'session.txt', tmp_path / 'session.jsonl'
    result = CliRunner().invoke(app, ['run', '--source', 'file', '--file', 'synthetic.wav', '--confirm-f0',
        '--export-text', str(text), '--export-jsonl', str(data)])
    assert result.exit_code == 0, result.output
    records = [json.loads(line) for line in data.read_text().splitlines()]
    assert [r['type'] for r in records] == ['session', 'segment', 'gap', 'gap', 'segment']
    assert len({r['session_id'] for r in records}) == 1
    assert configs[0] is configs[1]  # Same credentials, region, and F0 assertion, no fallback.
    assert 'Reconnecting 1/3' in result.output and 'Audio gap' in result.output
    assert text.read_text().count('[gap]') == 2
    assert 'synthetic-not-a-real-key' not in result.output + text.read_text() + data.read_text()
