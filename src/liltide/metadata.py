"""Allowlisted run settings for exports; no environment or device inspection."""

from dataclasses import dataclass

from liltide import __version__


@dataclass(frozen=True)
class RunMetadata:
    input_type: str
    segmentation_silence_ms: int | None = None

    def __post_init__(self):
        if self.input_type not in {"system", "microphone", "file"}:
            raise ValueError("Unknown input type for run metadata.")
        if self.segmentation_silence_ms is not None and (
                type(self.segmentation_silence_ms) is not int or not 100 <= self.segmentation_silence_ms <= 5000):
            raise ValueError("Segmentation silence must be 100–5000 ms.")

    def record(self, session_id):
        return {
            "type": "session",
            "session_id": session_id,
            "schema_version": 1,
            "app_version": __version__,
            "provider": "azure_speech",
            "source_language": "pl-PL",
            "target_language": "en",
            "input_type": self.input_type,
            "segmentation_silence_ms": self.segmentation_silence_ms,
            "segmentation_mode": "service_default" if self.segmentation_silence_ms is None else "explicit_request",
        }

    def text(self, session_id):
        segmentation = ("service default (no override requested)" if self.segmentation_silence_ms is None
                        else f"{self.segmentation_silence_ms} ms (requested)")
        return (f"[session]\nLiltide: {__version__}\nSession: {session_id}\n"
                f"Provider: azure_speech\nLanguages: pl-PL -> en\nInput: {self.input_type}\n"
                f"Segmentation silence: {segmentation}\n\n")
