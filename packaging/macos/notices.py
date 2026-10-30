"""Collect available installed runtime license texts for the local bundle."""
from importlib.metadata import distribution
from pathlib import Path
import json
import shutil
from packaging.requirements import Requirement


def collect(destination):
    destination.mkdir(parents=True, exist_ok=True)
    pending = [('liltide', 'gui'), ('keyring', ''), ('pyinstaller', '')]
    visited, records = set(), []
    while pending:
        name, extra = pending.pop()
        normalized = name.lower().replace('_', '-')
        if (normalized, extra) in visited:
            continue
        visited.add((normalized, extra))
        dist = distribution(name)
        for requirement in dist.requires or []:
            req = Requirement(requirement)
            if req.marker is None or req.marker.evaluate({'extra': extra}):
                pending.extend((req.name, child_extra) for child_extra in (req.extras or {''}))
        folder = destination / normalized
        folder.mkdir(exist_ok=True)
        texts = []
        for file in dist.files or []:
            if not any(token in str(file).lower() for token in ('license', 'copying', 'notice')):
                continue
            source = Path(dist.locate_file(file))
            # Preserve nested paths to avoid replacing different LICENSE files.
            safe = Path(*[part for part in file.parts if part not in ('.', '..')])
            target = folder / safe
            if source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                texts.append(str(target.relative_to(destination)))
        records.append({'package': dist.metadata['Name'], 'version': dist.version,
                        'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                        'available_license_texts': texts})
    (destination / 'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
    (destination / 'README.txt').write_text(
        'Local personal-use build only. Available installed license texts are collected here.\n'
        'This is not a completed distribution compliance review. Qt/PySide and other\n'
        'components may require additional notices, license texts and source/relinking provisions.\n'
        'See the project docs/third-party.md before redistribution.\n')
