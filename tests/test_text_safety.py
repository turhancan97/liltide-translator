import io
import json

import pytest
from rich.console import Console

from liltide.exports import TranscriptExports
from liltide.events import Gap
from liltide.provider import Caption
from liltide.terminal import CaptionRenderer
from liltide.text_safety import safe_text


@pytest.mark.parametrize('payload', ['\x1b]52;c;synthetic\x07', '\x1b[2J', '\x9b2J\x9d',
                                    '\r\b\x00\x7f', '\nEN: forged\tline', '\u2028\u2029'])
def test_untrusted_caption_controls_are_visible_without_changing_json(tmp_path, payload):
    value = 'Zażółć gęślą jaźń ' + payload
    event = Caption('synthetic', 0, 100, value, value, True)
    buf = io.StringIO()
    renderer = CaptionRenderer(Console(file=buf, force_terminal=True, color_system=None, width=500), 'bilingual')
    renderer.caption(event)
    renderer.status(value)
    rendered = buf.getvalue()
    text, data = tmp_path/'synthetic.txt', tmp_path/'synthetic.jsonl'
    with TranscriptExports(text, data) as exports:
        exports.caption(event)
        exports.gap(Gap(100, 200, payload))
    for result in (rendered, text.read_text()):
        assert safe_text(value) in result
        assert not any(ord(c) < 32 and c != '\n' or 127 <= ord(c) <= 159 for c in result)
        assert '\nEN: forged' not in result
    records = [json.loads(line) for line in data.read_text().split('\n') if line]
    assert not any(ord(c) < 32 and c != '\n' or 127 <= ord(c) <= 159 for c in data.read_text())
    assert records[0]['source_text'] == value
    assert records[0]['translation_text'] == value
    assert records[1]['reason'] == payload


def test_all_c0_c1_controls_are_escaped_and_polish_is_unchanged():
    controls = ''.join(chr(code) for code in [*range(32), *range(127, 160)])
    assert all(ord(c) >= 32 and not 127 <= ord(c) <= 159 for c in safe_text(controls))
    assert safe_text('Zażółć gęślą jaźń — 42') == 'Zażółć gęślą jaźń — 42'


def test_provisional_caption_sanitization_uses_same_boundary():
    updates = []
    renderer = CaptionRenderer(Console(file=io.StringIO()), 'bilingual')
    class Live:
        def update(self, text):
            updates.append(text.plain)
    renderer.live = Live()
    renderer.caption(Caption('synthetic', 0, 100, 'PL\x1b[2J', 'EN\x9b2J', False))
    assert '\\x1b' in updates[0] and '\\x9b' in updates[0]
    assert '\x1b' not in updates[0] and '\x9b' not in updates[0]
