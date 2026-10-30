# Local macOS application

The existing Python/PySide6 GUI can be built as **Liltide.app** for opening from Finder or the Dock. This is an authorized local personal-use PoC, not a notarized public installer or a native Swift rewrite. Build on the Mac/architecture you intend to use. Intel Macs, older macOS versions and clean-machine installation remain unverified.

## Build

From the project directory in your existing virtual environment:

```console
python -m pip install -e ".[mac-app]"
python scripts/build_macos_app.py
```

The result is `dist/Liltide.app`. The build script replaces generated build output, collects available installed dependency license texts, bundles Python/Qt/audio/Azure libraries and brand resources, and applies PyInstaller's local ad-hoc signature. It does not install drivers, read your Azure key, create resources, or invoke capture/translation. Build output is ignored by Git. The bundled runtime does not depend on your development virtual environment at launch.

Open `dist` in Finder and double-click **Liltide**. You may copy the app to Applications and drag it to the Dock. Keep the whole `.app` bundle intact; shell copies/archives must preserve symbolic links. Building again updates `dist/Liltide.app`, not an earlier copy in Applications. There is no updater.

## First use

1. Open **Azure setup…**. Enter the key and region from your own Azure Speech **F0** resource and click **Save in Keychain**. Keep the key private. The field is masked; saved keys are never displayed. Saving does not contact Azure or verify the resource tier. macOS may ask permission to access Keychain; allow access only for your intended Liltide build.
2. Click **Refresh devices**, select the source type and exact input. For system audio, keep your existing BlackHole/multi-output routing so you can still hear the meeting through headphones. Liltide does not change routing or meeting-app microphone settings.
3. Verify F0 in Azure and check its confirmation box, then click **Start translation**. The app sends only the selected input's audio to Azure once started. No meeting detection or automatic capture is introduced.
4. Use Pause/Resume, Stop, and floating captions as in the [GUI guide](setup.md#desktop-gui-poc). Optional transcript exports require fresh filenames and explicit enabling for each run.

If macOS requests microphone/input access, the app has its own permission identity: terminal permission may not cover it. This is still subject to real-device validation. If denied, review macOS Privacy & Security settings for Liltide; do not assume a selected virtual input guarantees permission or correct routing.

## Credentials and saved choices

On macOS, the GUI explicitly uses the system Keychain backend, with service `org.liltide.translator.azure` and account `speech`. There is no plaintext or automatically discovered third-party backend fallback. **Forget saved Azure credentials** removes that item; errors remain visible if access is denied or the item is absent. Rebuilding or changing signatures may cause another Keychain permission prompt. Keychain access follows macOS access-control permissions; development GUI runs share their Python executable identity with other scripts using that interpreter. Review the credential’s Access Control in Keychain Access if you need a prompt on each read, as explained in [keyring’s security considerations](https://keyring.readthedocs.io/en/latest/#security-considerations). Existing GUI launches from a terminal keep environment credentials as the first choice: if either `AZURE_SPEECH_KEY` or `AZURE_SPEECH_REGION` is present, both must be valid; credentials are never mixed with the saved account. The CLI continues to use environment variables only. No `.env` files are automatically loaded.

Theme, caption size, view and source type are saved through Qt's platform settings (`Liltide` / `Liltide`). **Remember selected input after Start** is optional: it saves the selected persistent device UID and source type locally when Start is accepted. On a later launch/Refresh, only a unique exact UID match can be restored. Missing/ambiguous devices remain unselected; names/defaults/numeric IDs are never used as a replacement. Device UIDs are local identifying settings, not export metadata. Uncheck Remember to remove that saved identity.

F0 confirmation, export paths/toggles, transcript history, audio, window geometry, timing toggle and floating-window visibility are not saved. Startup remains idle, with no automatic discovery or capture. Windows/Linux keep their current environment-credential and in-memory GUI behavior.

## Verification and distribution limits

The reproducible **offline** bundled diagnostic exercises Qt windows, a real spawned child, audio/Azure imports and resampling with synthetic silence. It does not access Keychain, enumerate devices, open capture, or contact Azure. Pass a new diagnostic report path explicitly:

```console
QT_QPA_PLATFORM=offscreen dist/Liltide.app/Contents/MacOS/Liltide --local-smoke-test /tmp/liltide-app-smoke.json
```

The diagnostic also uses a temporary settings file beside its report. It reports only pass/fail/GUI-backend information. A successful diagnostic is not a live meeting test or proof of Finder permissions. See [validation evidence](validation.md#local-macos-app--2026-10-30).

The user confirmed the local app works on their macOS setup on 2026-10-30. Individual checklist outcomes and duration were not supplied. Detailed evidence for Finder launch, masked setup, actual Keychain save/read/remove, virtual-input discovery/capture, and Stop/quit remains open. Live cloud testing requires explicit operator invocation against confirmed F0. Existing deferred long-session, accuracy and Windows/Linux checks remain deferred.

Public distribution needs a separate signing/notarization and [third-party compliance review](third-party.md). The local app is not Developer ID signed or notarized; do not treat it as a public release. Build tooling follows [PyInstaller's bundle documentation](https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle) and [multiprocessing guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing); credential storage follows the [keyring API](https://keyring.readthedocs.io/en/latest/), with backend selection deliberately restricted. Sources checked 2026-10-30.
