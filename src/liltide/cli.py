"""Capture diagnostics and explicitly enabled Azure F0 translated captions."""

from contextlib import closing
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
import os
import platform
from pathlib import Path
import time
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from liltide import __version__
from liltide.audio import AudioError, SoundCardBackend, backend_hint
from liltide.capture import capture_levels

app = typer.Typer(no_args_is_help=True, invoke_without_command=True, add_completion=False, pretty_exceptions_enable=False,
                  help="Liltide: local audio diagnostics and Polish-to-English captions via Azure F0.")


class Source(str, Enum):
    system = "system"
    microphone = "microphone"
    file = "file"


class View(str, Enum):
    bilingual = "bilingual"
    english = "english"


def console():
    plain = "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb"
    return Console(no_color=plain, force_terminal=False if plain else None, highlight=False)


def fail(message):
    console().print(f"Error: {message}", markup=False)
    raise typer.Exit(1)


@app.callback()
def main(version_flag: Annotated[bool, typer.Option("--version", is_eager=True)] = False):
    if version_flag:
        console().print(f"Liltide {__version__}")
        raise typer.Exit()


@app.command()
def devices():
    """List exact capture device IDs without recording audio."""
    out = console()
    try:
        backend = SoundCardBackend()
        inputs = backend.devices()
    except AudioError as exc:
        fail(str(exc))
    table = Table(title="Local capture sources", box=None)
    for column in ("ID (copy exactly)", "Name", "Type", "Channels"):
        table.add_column(column, overflow="fold", no_wrap=False)
    for device in inputs:
        table.add_row(Text(device.id), Text(device.name), device.kind, str(device.channels))
    out.print(table)
    if not inputs:
        out.print("No capture inputs found. " + backend_hint(backend.system))
    if backend.system == "Darwin":
        out.print("macOS inputs cannot be classified automatically. For system audio, select your manually routed virtual input; physical microphones are not system audio.")
    out.print("Native sample rates are not exposed consistently; capture requests 48000 Hz by default. IDs may change between sessions.")


@app.command()
def doctor(cloud: Annotated[bool, typer.Option("--cloud")] = False):
    """Check local dependencies and source visibility; never record or contact cloud."""
    if cloud:
        fail("Cloud doctor is not implemented. Use an explicitly confirmed F0 translation session; local doctor makes no cloud calls.")
    out = console()
    out.print(f"Liltide {__version__} | Python {platform.python_version()} | {platform.system()} {platform.release()} | {platform.machine()}")
    for name in ("typer", "rich", "SoundCard", "numpy", "soxr", "azure-cognitiveservices-speech"):
        try:
            out.print(f"{name}: {version(name)}")
        except PackageNotFoundError:
            fail(f"{name} is missing. Reinstall with 'python -m pip install -e .'.")
    try:
        backend = SoundCardBackend()
        inputs = backend.devices()
    except AudioError as exc:
        fail(str(exc))
    out.print(f"Input discovery: {len(inputs)} device(s); names omitted from diagnostics.")
    out.print(backend_hint(backend.system))
    out.print("Permissions, routing, sample-rate support, and audible playback are NOT verified by discovery. Run an explicit audio-level check.")
    out.print("Cloud: disabled. No audio captured, saved, or transmitted.")
    if not inputs:
        raise typer.Exit(1)


@app.command()
def run(
    check_audio: Annotated[bool, typer.Option("--check-audio", help="Capture levels locally; no saving/transmission.")] = False,
    source: Annotated[Source, typer.Option("--source")] = Source.system,
    device: Annotated[str | None, typer.Option("--device", help="Exact ID from 'liltide devices'.")] = None,
    sample_rate: Annotated[int, typer.Option("--sample-rate", min=8000, max=192000)] = 48000,
    duration: Annotated[float | None, typer.Option("--duration", min=0.1, max=3600, help="Stop after N seconds (meter: first frame; translation: stream ready, including pauses).")] = None,
    file: Annotated[Path | None, typer.Option("--file", help="PCM16 mono/stereo WAV input (requires --source file).")] = None,
    view: Annotated[View, typer.Option("--view")] = View.bilingual,
    confirm_f0: Annotated[bool, typer.Option("--confirm-f0", help="Confirm you checked this Azure resource uses the free F0 tier.")] = False,
    export_text: Annotated[Path | None, typer.Option("--export-text", help="Save run settings, bilingual captions, and gaps to a new UTF-8 file.")] = None,
    export_jsonl: Annotated[Path | None, typer.Option("--export-jsonl", help="Save run settings, finalized captions, and gaps to a new JSONL file.")] = None,
    segmentation_silence_ms: Annotated[int | None, typer.Option("--segmentation-silence-ms", min=100, max=5000,
        help="Experimental Azure pause threshold; e.g. 300 for shorter phrases. Default: service setting. Not a phrase-length limit.")] = None,
    show_timing: Annotated[bool, typer.Option("--show-timing", help="Show caption arrival details and an estimated-delay summary on exit.")] = False,
):
    """Translate selected audio, or check levels locally. Ctrl+C stops."""
    if source == Source.file:
        if not file or device or check_audio:
            fail("--source file requires --file and is incompatible with --device or --check-audio.")
    elif file:
        fail("--file requires --source file.")
    if check_audio and (export_text is not None or export_jsonl is not None):
        fail("--check-audio is incompatible with transcript exports.")
    if check_audio and show_timing:
        fail("--show-timing is only available for translated captions, not --check-audio.")
    if not check_audio:
        if source != Source.file and not device:
            fail("--device is required for live input. Run 'liltide devices'.")
        try:
            from liltide.provider import AzureProvider, CloudConfig
            from liltide.session import TranslationSession
            from liltide.sources import LiveSource, WaveSource
            from liltide.terminal import CaptionRenderer, PauseControl
            from liltide.exports import TranscriptExports
            from liltide.metadata import RunMetadata
            config = CloudConfig.from_environment(confirm_f0, segmentation_silence_ms)
            if source != Source.file:
                # Reject wrong source/IDs before initializing any cloud resource.
                SoundCardBackend().select(device, source.value)
            out = console()
            out.print("Cloud mode: selected audio will be sent to Azure. --confirm-f0 is your assertion, not a billing-tier check. Raw audio is never saved locally.")
            if segmentation_silence_ms is not None:
                out.print(f"Experimental segmentation pause threshold: {segmentation_silence_ms} ms. Shorter phrases can reduce context; translation-service behavior requires live validation.")
            if export_text is not None or export_jsonl is not None:
                out.print("Transcript export enabled: finalized Polish and English text will be saved, independently of --view. Existing files will not be overwritten.")
            else:
                out.print("Transcript export disabled: no transcript files are saved.")
            if platform.system() == "Darwin" and source == Source.system:
                out.print("Select a manually routed virtual input for system audio; source type cannot be inferred on macOS.")
            factory = (lambda: WaveSource(file)) if source == Source.file else (
                lambda: LiveSource(device, source.value, sample_rate))
            metadata = RunMetadata(source.value, config.segmentation_silence_ms)
            with TranscriptExports(export_text, export_jsonl, metadata=metadata) as exports, CaptionRenderer(out, view.value, show_timing) as renderer, PauseControl() as controls:
                session = TranslationSession(factory, lambda: AzureProvider(config), renderer.caption,
                    renderer.status, controls, file_input=source == Source.file, duration=duration,
                    on_finalized=exports.caption, on_gap=exports.gap)
                try:
                    session.run()
                finally:
                    if show_timing:
                        renderer.timing_summary(session.timing_summary())
        except AudioError as exc:
            fail(str(exc))
        return
    if confirm_f0 or view != View.bilingual or segmentation_silence_ms is not None:
        fail("--check-audio is incompatible with --confirm-f0, --view english, or segmentation options.")
    if not device:
        fail("--device is required. Run 'liltide devices' and copy an exact ID.")
    out = console()
    out.print("Starting local audio-level capture. No audio is saved or transmitted. Ctrl+C stops.")
    if platform.system() == "Darwin" and source == Source.system:
        out.print("Confirm the selected input is your routed virtual device; macOS cannot distinguish it from a microphone.")
    last_print = -float("inf")
    def render(level):
        fill = int(min(30, max(0, (level.rms_dbfs + 60) / 2)))
        state = "CLIPPING" if level.clipping else "SILENCE/LOW" if level.rms_dbfs < -60 else "SIGNAL"
        return Text(f"[{state}] [{'#' * fill}{'-' * (30 - fill)}] RMS {level.rms_dbfs:6.1f} dBFS | peak {level.peak_dbfs:6.1f} dBFS")
    try:
        with closing(capture_levels(device, source.value, sample_rate, duration)) as levels:
            if out.is_terminal:
                with Live(Text("Waiting for audio frames…"), console=out, refresh_per_second=10) as live:
                    for level in levels:
                        live.update(render(level))
            else:
                for level in levels:
                    if time.monotonic() - last_print >= 1:
                        out.print(render(level))
                        last_print = time.monotonic()
    except KeyboardInterrupt:
        out.print("Stopped. Audio capture released.")
        return
    except AudioError as exc:
        fail(str(exc))
    out.print("Finished. Audio capture released.")
