import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location('check_docs', Path(__file__).parents[1]/'scripts/check_docs.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_links_images_references_encoded_paths_and_duplicate_headings(tmp_path):
    target = tmp_path/'two words.md'
    target.write_text('# Same `name`\n\n# Same name\n', encoding='utf-8')
    (tmp_path/'symbol.svg').write_text('<svg/>')
    source = tmp_path/'README.md'
    source.write_text('''# Start
[reference][target]
[second](two%20words.md#same-name-1)
![symbol](symbol.svg)
[self](#start)
[external](https://example.invalid/never-requested)

[target]: <two words.md#same-name>

```markdown
[example](does-not-exist.md)
```
''', encoding='utf-8')
    assert checker.check_file(source, tmp_path) == []


def test_broken_targets_anchors_and_outside_links_are_detected(tmp_path):
    source = tmp_path/'README.md'
    source.write_text('# Start\n[bad](#absent)\n![bad](missing.svg)\n[bad](../outside.md)\n')
    assert [reason for _, reason in checker.check_file(source, tmp_path)] == [
        'missing heading', 'missing file', 'outside repository']
