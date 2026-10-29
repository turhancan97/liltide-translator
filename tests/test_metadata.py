import json
import wave

import pytest
from typer.testing import CliRunner

from liltide import __version__
from liltide.audio import AudioError
from liltide.cli import app
from liltide.events import Gap
from liltide.exports import TranscriptExports
from liltide.metadata import RunMetadata
from liltide.provider import Caption


@pytest.mark.parametrize('silence_ms,mode', [(None, 'service_default'), (300, 'explicit_request')])
def test_header_written_and_synced_before_captions(tmp_path, silence_ms, mode):
    text, data = tmp_path / 'session.txt', tmp_path / 'session.jsonl'
    with TranscriptExports(text, data, metadata=RunMetadata('file', silence_ms)) as sink:
        rows = [json.loads(line) for line in data.read_text().splitlines()]
        assert rows == [dict(type='session', session_id=sink.session_id, schema_version=1,
            app_version=__version__, provider='azure_speech', source_language='pl-PL', target_language='en',
            input_type='file', segmentation_silence_ms=silence_ms, segmentation_mode=mode)]
        assert text.read_text().startswith('[session]\n')
        assert f'Session: {sink.session_id}' in text.read_text()
        assert 'service default' in text.read_text() if silence_ms is None else '300 ms (requested)' in text.read_text()
        sink.caption(Caption('0', 0, 100, 'Test', 'Test', True))
        sink.gap(Gap(100, 200, 'connection_failure'))
        rows = [json.loads(line) for line in data.read_text().splitlines()]
        assert [r['type'] for r in rows] == ['session', 'segment', 'gap']
        assert len({r['session_id'] for r in rows}) == 1


@pytest.mark.parametrize('kwargs', [dict(input_type='private-device-name'),
    dict(input_type='file', segmentation_silence_ms=99),
    dict(input_type='system', segmentation_silence_ms=5001),
    dict(input_type='microphone', segmentation_silence_ms='300'),
    dict(input_type='file', segmentation_silence_ms=300.5)])
def test_invalid_metadata_is_rejected_before_export_creation(tmp_path, kwargs):
    with pytest.raises(ValueError):
        TranscriptExports(jsonl_path=tmp_path / 'session.jsonl', metadata=RunMetadata(**kwargs))
    assert list(tmp_path.iterdir()) == []


def test_no_sidecar_or_default_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TranscriptExports(metadata=RunMetadata('system', 300)):
        pass
    assert list(tmp_path.iterdir()) == []
    with TranscriptExports(text_path=tmp_path / 'session.txt', metadata=RunMetadata('microphone')):
        pass
    assert [p.name for p in tmp_path.iterdir()] == ['session.txt']


def test_metadata_failure_closes_all_files(tmp_path, monkeypatch):
    sink = TranscriptExports(tmp_path / 'session.txt', tmp_path / 'session.jsonl', metadata=RunMetadata('file'))
    files = []
    def failed_write(record, text):
        files.extend(file for _, _, file in sink.files)
        raise AudioError('Synthetic header write failure')
    monkeypatch.setattr(sink, '_write', failed_write)
    with pytest.raises(AudioError, match='header write failure'):
        with sink:
            raise AssertionError('Must not enter a failed exporter')
    assert len(files) == 2 and all(file.closed for file in files)
    assert not sink.files


class FakeSource:
    rate = 16000
    def resume(self):
        pass
    def read(self):
        raise StopIteration
    def close(self):
        pass


class FakeProvider:
    def start(self):
        pass
    def poll(self):
        return [Caption('0', 0, 100, 'Test', 'Test', True)]
    def write(self, data):
        pass
    def finish(self):
        return iter(())
    def abort(self):
        pass


@pytest.mark.parametrize('source', ['system', 'microphone', 'file'])
@pytest.mark.parametrize('silence_ms', [None, 300])
def test_cli_header_records_selected_settings_but_no_identifiers(tmp_path, monkeypatch, source, silence_ms):
    from liltide import cli, provider, sources
    secret = 'synthetic-key-must-not-be-exported'
    monkeypatch.setenv('AZURE_SPEECH_KEY', secret)
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    monkeypatch.setattr(provider, 'AzureProvider', lambda config: FakeProvider())
    monkeypatch.setattr(sources, 'LiveSource', lambda *args: FakeSource())
    monkeypatch.setattr(cli, 'SoundCardBackend', lambda: type('Backend', (), {'select': lambda *args: None})())
    path = tmp_path / 'session.jsonl'
    args = ['run', '--source', source, '--confirm-f0', '--export-jsonl', str(path)]
    if source == 'file':
        audio = tmp_path / 'private-recording-name.wav'
        with wave.open(str(audio), 'wb') as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(16000)
            file.writeframes(b'')
        args += ['--file', str(audio)]
    else:
        args += ['--device', 'private-device-identifier']
    if silence_ms is not None:
        args += ['--segmentation-silence-ms', str(silence_ms)]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    data = path.read_text()
    rows = [json.loads(line) for line in data.splitlines()]
    header = rows[0]
    assert header['type'] == 'session' and header['input_type'] == source
    assert header['segmentation_silence_ms'] == silence_ms
    assert header['app_version'] == __version__
    for forbidden in (secret, 'private-recording-name', 'private-device-identifier', 'westeurope', str(tmp_path)):
        assert forbidden not in data


def test_cli_header_failure_prevents_source_and_provider_startup(tmp_path, monkeypatch):
    from liltide import provider, sources
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'westeurope')
    def forbidden(*args):
        raise AssertionError('Source/provider must not start after a header failure')
    monkeypatch.setattr(provider, 'AzureProvider', forbidden)
    monkeypatch.setattr(sources, 'WaveSource', forbidden)
    def failed_write(*args):
        raise AudioError('Synthetic header flush failure')
    monkeypatch.setattr(TranscriptExports, '_write', failed_write)
    result = CliRunner().invoke(app, ['run', '--source', 'file', '--file', 'unused.wav', '--confirm-f0',
        '--export-jsonl', str(tmp_path / 'session.jsonl')])
    assert result.exit_code == 1 and 'header flush failure' in result.output
