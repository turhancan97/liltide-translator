"""Explicit, append-only session exports. No files are opened without opt-in."""

import json
import os
from pathlib import Path
from uuid import uuid4

from liltide.audio import AudioError
from liltide.formatting import timestamp


class TranscriptExports:
    def __init__(self, text_path=None, jsonl_path=None):
        self.destinations = [(kind, Path(path)) for kind, path in
                             (("text", text_path), ("jsonl", jsonl_path)) if path is not None]
        self.session_id = uuid4().hex
        self.files = []

    def __enter__(self):
        try:
            return self._open()
        except (OSError, RuntimeError, ValueError) as exc:
            raise AudioError("Cannot prepare export paths. Check filenames, parent directories, and permissions.") from exc

    def _open(self):
        resolved = [path.resolve() for _, path in self.destinations]
        if len(set(resolved)) != len(resolved):
            raise AudioError("Text and JSONL exports must use different paths.")
        # Validate the pair before creating either file. Exclusive creation below
        # still protects against a destination appearing after this check.
        for _, path in self.destinations:
            if path.exists() or path.is_symlink():
                raise AudioError("Export destination already exists; choose a new filename. Nothing was overwritten.")
            if not path.parent.is_dir():
                raise AudioError("Export parent directory does not exist; create it before starting.")
        try:
            for kind, path in self.destinations:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    file = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
                except BaseException:
                    os.close(fd)
                    raise
                self.files.append((kind, path, file))
        except OSError as exc:
            # Roll back only empty files created by this attempt, never an existing
            # destination or a path replaced by someone else.
            for _, path, file in self.files:
                identity = os.fstat(file.fileno())
                file.close()
                try:
                    current = path.lstat()
                    if (current.st_dev, current.st_ino, current.st_size) == (identity.st_dev, identity.st_ino, 0):
                        path.unlink()
                except OSError:
                    pass
            self.files.clear()
            raise AudioError("Cannot create export files. Check directory permissions and choose new filenames; capture has not started.") from exc
        return self

    def caption(self, event):
        if not event.final or not event.has_content:
            return
        record = {
            "type": "segment",
            "session_id": self.session_id,
            "segment_id": event.segment_id,
            "start_ms": event.start_ms,
            "end_ms": event.end_ms,
            "source_language": "pl-PL",
            "target_language": "en",
            "source_text": event.polish,
            "translation_text": event.english,
        }
        english = event.english if event.english is not None else "[translation unavailable]"
        text = (f"[{timestamp(event.start_ms)} --> {timestamp(event.end_ms)}] [final]\n"
                f"PL: {event.polish}\nEN: {english}\n\n")
        self._write(record, text)

    def gap(self, event):
        record = {"type": "gap", "session_id": self.session_id, "start_ms": event.start_ms,
                  "end_ms": event.end_ms, "reason": event.reason}
        text = (f"[{timestamp(event.start_ms)} --> {timestamp(event.end_ms)}] [gap]\n"
                f"Reason: {event.reason} (audio may be missing or unfinalized)\n\n")
        self._write(record, text)

    def _write(self, record, text):
        for kind, _, file in self.files:
            if kind == "jsonl":
                payload = json.dumps(record, ensure_ascii=False) + "\n"
            else:
                payload = text
            try:
                if file.write(payload) != len(payload):
                    raise OSError("Incomplete write")
                file.flush()
                os.fsync(file.fileno())
            except (OSError, UnicodeError) as exc:
                raise AudioError(f"{kind.upper()} export write/flush failed. Session stopped; previously saved segments remain. The last record may be incomplete and paired exports may differ.") from exc

    def __exit__(self, exc_type, exc, traceback):
        failures = []
        for kind, _, file in self.files:
            try:
                file.close()
            except OSError:
                failures.append(kind)
        self.files.clear()
        if failures and exc_type is None:
            raise AudioError("Export close failed; inspect the saved files for an incomplete last record.")
