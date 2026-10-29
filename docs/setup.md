# Intended platform setup

**Capture and translation PoC available.** Local capture and user-reported lecture routing work on this Mac. Translation has offline tests and a user-confirmed successful live macOS session; no independent agent cloud test has been run. Other-platform installation/capture remain unverified. No drivers, cloud resources, or credentials are supplied.

## Install and check locally

Python 3.11+ is required; the current local run uses Python 3.13.7. From the project directory:

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
liltide devices
liltide doctor
liltide run --check-audio --source system --device DEVICE_ID --duration 10
```

Windows PowerShell: use `py -3 -m venv .venv`, then `.venv\Scripts\Activate.ps1`; the remaining commands are the same. Shell activation is optional: invoke `.venv/bin/liltide` directly on macOS/Linux, or `.venv\Scripts\liltide.exe` on Windows.

Select an exact ID from `devices`, quoted if necessary. Use `--source microphone` for microphone capture. Omit `--duration` for continuous checks; Ctrl+C releases capture. `--sample-rate` defaults to 48000 Hz. The meter reports RMS/peak dBFS plus SIGNAL, SILENCE/LOW, or CLIPPING; silence or a moving meter alone does not prove correct routing. Non-finite samples and unsupported devices fail explicitly. In a non-interactive terminal it prints approximately one update per second; interactive output refreshes in place. `NO_COLOR` or `TERM=dumb` disables colored/animated terminal presentation.

Run synthetic/offline tests with `python -m pytest -q`. Translation requires explicitly confirmed Azure F0 configuration as described below. WAV input and interactive pause/resume are implemented; exports, automatic reconnect, and `doctor --cloud` are not.

If discovery returns zero devices inside a sandbox but succeeds in a normal terminal, test from that terminal. `doctor` does not verify recording permissions, and this project does not grant them automatically.

## Shared prerequisites

During the capture milestone, record OS version, architecture, Python version (3.11+), package versions, and native audio backend. Resolve supported SDK wheels and native dependencies before fixing a compatibility matrix. Use a project virtual environment. A GPU is not required by the planned cloud design.

First validate local audio routing using the implemented `devices`, `doctor`, and `run --check-audio` commands in the [technical specification](technical-spec.md). Play a non-private reference clip, confirm level activity, stop playback and check levels fall, and verify the original audio remains audible. Disconnect/reconnect the device and inspect diagnostics. No cloud transmission is needed for this phase.

## Windows: WASAPI loopback

1. Choose the playback endpoint carrying the lecture (for example, the current headphones).
2. Select that endpoint's loopback source in Liltide; a microphone is a separate source.
3. Keep the lecture playing through the normal endpoint; loopback should not require changing its output route.
4. Validate channel conversion and device switching, including Bluetooth behavior on the actual hardware.

[SoundCard](https://github.com/bastibe/SoundCard) uses WASAPI on Windows and documents capture/channel limitations. Do not assume single-channel device recording is safe; capture the necessary channels and downmix. OS/architecture compatibility remains untested here.

## Linux: monitor source

1. Use PulseAudio or PipeWire with its PulseAudio compatibility service enabled.
2. Route the lecture to the intended output sink and select its monitor as Liltide's source.
3. Keep the sink routed to headphones/speakers so the lecture remains audible.
4. Verify permissions, source visibility, rate conversion, and behavior when the default sink changes.

The chosen SoundCard backend uses PulseAudio; native ALSA-only setups are outside the initial approach. Refer to [SoundCard's backend documentation](https://github.com/bastibe/SoundCard). No distribution or audio-server combination has been tested by Liltide yet.

## macOS: virtual audio input

1. Manually install a virtual audio device, such as BlackHole, using its official instructions. Installation is separate from Liltide; no driver is bundled.
2. In Audio MIDI Setup, create a Multi-Output Device containing the virtual device and the headphones/speakers you want to hear. Follow the driver's clock/drift-correction guidance.
3. Route lecture/system playback to the Multi-Output Device.
4. Select the virtual device as Liltide's input, rather than selecting the physical microphone.
5. Grant the launching terminal/app the input permissions macOS requests. Verify capture and audible playback independently.
6. Restore the normal output device after testing if desired. Avoid routing captured audio back into its own input.

See [BlackHole's official repository and Multi-Output guidance](https://github.com/ExistentialAudio/BlackHole). Multi-output volume controls and Bluetooth behavior can differ from normal playback. SoundCard's current macOS backend does not provide the loopback path used on Windows; virtual routing is the initial workaround. Native system capture is deferred.

## Azure F0: translation PoC

1. Check current account eligibility, region availability, allowance, and restrictions using the [provider guide](providers.md).
2. Manually create or choose an Azure Speech resource with the **F0** SKU. If unavailable, stop and report the limitation; do not substitute S0 or use promotional paid-tier credit as approval.
3. Inspect the actual resource's pricing tier in Azure. Cloud billing configuration is the operator's responsibility; a key or a locally declared tier does not verify it.
4. Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` locally. Never put secrets in CLI flags, documentation, screenshots, or committed files. The SDK receives these through Liltide's configuration adapter.
5. Only explicitly invoke cloud diagnostics/tests after confirming F0. Use non-private audio. The CLI discloses transmission when a cloud session starts.
6. On quota exhaustion, stop. Do not upgrade, add a paid provider, or continue by switching resources automatically.

The user confirmed a successful live translation session after setup. The agent has not inspected the resource or run a cloud test. Resource provisioning is a separate manual step; never share the key in chat.

After creating an F0 Speech resource, open its Keys and Endpoint page to obtain the key and **region identifier** (for example `westeurope`, not an endpoint URL). Set them in the same terminal that runs Liltide. On macOS/Linux Bash or Zsh, enter the key through a hidden prompt so the value is not embedded in shell history:

```bash
export AZURE_SPEECH_REGION=westeurope
read -r -s AZURE_SPEECH_KEY
export AZURE_SPEECH_KEY
```

After the `read` command, paste the key and press Enter; nothing is echoed. Replace the example region with the actual resource region. In Windows PowerShell:

```powershell
$env:AZURE_SPEECH_REGION = "westeurope"
$env:AZURE_SPEECH_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Azure Speech key" -AsSecureString)).Password
```

Liltide reads environment variables, not `.env` files. It does not persist keys. Run explicitly:

```console
liltide run --source system --device DEVICE_ID --confirm-f0
liltide run --source microphone --device DEVICE_ID --confirm-f0
liltide run --source file --file lecture.wav --confirm-f0 --view english
```

Use a short non-private Polish clip first. The tier confirmation flag is an operator assertion, not an Azure billing check. Do not pass it for S0. `--duration 30` bounds session wall time after stream readiness, including pauses; initialization/shutdown add some time. Press `p` to pause/resume when stdin is an interactive terminal; capture and the recognizer are released during pause. WAV replay retains its cursor. Resumption creates fresh recognition context. Ctrl+C stops and attempts a bounded final drain.

Provisional text appears in place only in an interactive display; finalized captions are printed once with elapsed timestamps. `--view english` omits Polish display but recognition still uses Polish. Plain/piped output contains finalized captions and status lines without cursor control. Errors, queue overflow, and connection loss stop the PoC instead of silently dropping audio or automatically reconnecting. Read any final-drain warning: the last unfinished caption can be missing.

The cloud SDK has its own internal buffers and service behavior; application queue limits are not proof of network delivery or a guaranteed latency bound. `doctor` remains entirely local; `doctor --cloud` deliberately fails without contacting Azure.

## File input and exports

Implemented file support is uncompressed PCM16 WAV, mono or stereo; rate conversion happens in the pipeline. Use synthetic or consented recordings kept outside version control. Text/JSONL export flags are not implemented yet. No local audio or transcript output files are created by the PoC; later opt-in exports should stay outside version control.
