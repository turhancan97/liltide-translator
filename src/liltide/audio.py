"""Local audio discovery; native libraries load only when explicitly requested."""

from dataclasses import dataclass, field
import importlib
import platform


class AudioError(Exception):
    """An actionable local capture failure."""


def backend_hint(system: str) -> str:
    if system == "Darwin":
        return "Check macOS input permission for your terminal and virtual audio routing (docs/setup.md)."
    if system == "Linux":
        return "Check libpulse and a running PulseAudio or PipeWire-Pulse service (docs/setup.md)."
    if system == "Windows":
        return "Check Windows input permissions and that the WASAPI playback endpoint is connected."
    return "Only Windows, macOS, and Linux are targeted."


@dataclass(frozen=True)
class InputIdentity:
    # Cross-process identity is private session state, never export metadata.
    id: str = field(repr=False)
    uid: str = field(repr=False)


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    channels: int
    kind: str
    uid: str | None = field(default=None, repr=False)

    @property
    def selection(self):
        return InputIdentity(self.id, self.uid) if self.uid is not None else self.id


class SoundCardBackend:
    def __init__(self):
        self.system = platform.system()
        if self.system not in {"Darwin", "Linux", "Windows"}:
            raise AudioError(backend_hint(self.system))
        try:
            self.sc = importlib.import_module("soundcard")
        except Exception as exc:
            raise AudioError(
                f"Audio backend unavailable ({type(exc).__name__}). {backend_hint(self.system)}"
            ) from exc

    def inputs(self):
        # macOS has no SoundCard loopback path; its virtual devices are ordinary inputs.
        return self.sc.all_microphones(include_loopback=self.system != "Darwin")

    def devices(self) -> list[Device]:
        try:
            return [
                Device(
                    str(m.id), str(m.name), int(m.channels),
                    "routed input" if self.system == "Darwin" else
                    "system" if m.isloopback else "microphone",
                    self._uid(m) if self.system == "Darwin" else None,
                )
                for m in self.inputs()
            ]
        except Exception as exc:
            raise AudioError(f"Cannot enumerate inputs. {backend_hint(self.system)}") from exc

    def _uid(self, mic):
        from liltide.coreaudio_identity import device_uid
        uid = device_uid(mic.id)
        if not uid:
            raise ValueError('Empty persistent identity')
        return uid

    def bind(self, device_id, source):
        """Validate and bind a numeric selection before crossing a spawn boundary."""
        mic = self.select(device_id, source)
        if isinstance(device_id, InputIdentity) or self.system != "Darwin":
            return device_id
        try:
            return InputIdentity(str(mic.id), self._uid(mic))
        except Exception as exc:
            raise AudioError('Cannot read selected persistent identity. Refresh devices; no fallback was selected.') from exc

    def select(self, device_id: str | InputIdentity, source: str):
        try:
            inputs = self.inputs()
            if isinstance(device_id, InputIdentity):
                if self.system != "Darwin" or not device_id.uid:
                    raise AudioError('Persistent identity is invalid for this backend. No fallback was selected.')
                id_present = any(str(m.id) == device_id.id for m in inputs)
                summary = f'inputs={len(inputs)}; previous_numeric_id_present={"yes" if id_present else "no"}'
                try:
                    matches = [m for m in inputs if self._uid(m) == device_id.uid]
                except Exception as exc:
                    raise AudioError(f'Persistent identity lookup unavailable ({summary}). Refresh devices or restart the app. No fallback was selected.') from exc
                if not matches:
                    raise AudioError(f'Selected persistent identity is missing ({summary}). Reconnect the selected device and refresh. No fallback was selected.')
                if len(matches) != 1:
                    raise AudioError(f'Selected persistent identity is ambiguous ({summary}). No fallback was selected.')
            else:
                matches = [m for m in inputs if str(m.id) == device_id]
            if not matches:
                raise AudioError(f"Device ID not found (inputs={len(inputs)}). Run 'liltide devices' again or Refresh devices; IDs may change.")
            if len(matches) != 1:
                raise AudioError("Device ID is ambiguous; reconnect the endpoint and list devices again.")
            mic = matches[0]
            if self.system != "Darwin":
                expected_loopback = source == "system"
                if bool(mic.isloopback) != expected_loopback:
                    raise AudioError(f"Selected device is not a {source} source. No fallback was selected.")
            if int(mic.channels) < 1:
                raise AudioError("Selected input has no capture channels.")
            if self.system == "Windows" and int(mic.channels) == 1:
                raise AudioError("Mono WASAPI capture is not supported by this backend reliably. Select a multichannel endpoint.")
            return mic
        except AudioError:
            raise
        except Exception as exc:
            raise AudioError(f"Cannot select input. {backend_hint(self.system)}") from exc
