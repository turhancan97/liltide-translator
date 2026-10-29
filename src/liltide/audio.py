"""Local audio discovery; native libraries load only when explicitly requested."""

from dataclasses import dataclass
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
class Device:
    id: str
    name: str
    channels: int
    kind: str


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
                )
                for m in self.inputs()
            ]
        except Exception as exc:
            raise AudioError(f"Cannot enumerate inputs. {backend_hint(self.system)}") from exc

    def select(self, device_id: str, source: str):
        try:
            matches = [m for m in self.inputs() if str(m.id) == device_id]
            if not matches:
                raise AudioError("Device ID not found. Run 'liltide devices' again; IDs may change.")
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
