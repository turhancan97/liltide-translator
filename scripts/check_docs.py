"""Check repository Markdown links/images and heading anchors, locally."""

from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

PARSER = MarkdownIt()


def anchors(text):
    tokens = PARSER.parse(text)
    used = set()
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        children = tokens[index + 1].children or []
        title = ''.join(child.content for child in children
                        if child.type in ('text', 'code_inline', 'image'))
        base = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        slug, number = base, 0
        while slug in used:
            number += 1
            slug = f'{base}-{number}'
        used.add(slug)
    return used


def check_file(path, root):
    """No network requests; skip external URLs and links inside code blocks."""
    root = root.resolve()
    failures = []
    for token in PARSER.parse(path.read_text(encoding='utf-8')):
        for child in token.children or []:
            attribute = {'link_open': 'href', 'image': 'src'}.get(child.type)
            if not attribute:
                continue
            link = child.attrGet(attribute)
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
            if not target.is_relative_to(root):
                failures.append((link, 'outside repository'))
            elif not target.is_file():
                failures.append((link, 'missing file'))
            elif parsed.fragment and target.suffix.lower() == '.md':
                if unquote(parsed.fragment) not in anchors(target.read_text(encoding='utf-8')):
                    failures.append((link, 'missing heading'))
    return failures


def main():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard',
                             '-z', '--', '*.md'], cwd=root,
                            check=True, capture_output=True)
    paths = [root / name for name in result.stdout.decode().split('\0') if name]
    failures = [(path.relative_to(root), link, reason)
                for path in paths for link, reason in check_file(path, root)]
    for path, link, reason in failures:
        # repr prevents malformed document links emitting terminal controls.
        print(f'{str(path)!r}: {reason}: {link!r}')
    print(f'Checked {len(paths)} repository Markdown files; {len(failures)} failures.')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
