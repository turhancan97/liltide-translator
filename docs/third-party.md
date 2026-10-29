# Licensing and third-party components

Original Liltide code, documentation, and SVG assets use the [MIT License](../LICENSE). No third-party source, font, logo, model weight, SDK binary, or driver is bundled in the repository. Development dependencies installed in the ignored local virtual environment retain their upstream terms.

## Planned dependencies

The technical baseline references Typer, Rich, SoundCard, NumPy, a resampling library (initial candidate: python-soxr), Azure Speech SDK, and later PySide6. Before implementation/distribution, inspect the exact selected versions and their transitive/native dependency licenses, record required notices, and resolve compatibility with the project's distribution model. A package's Python wrapper license may differ from its native libraries.

Azure service terms, SDK terms, data handling, and F0 restrictions are separate from Liltide's MIT license. Naming a service does not imply endorsement or extend MIT to the service.

## Audio routing and test media

macOS virtual drivers are user-installed separately. [BlackHole](https://github.com/ExistentialAudio/BlackHole) is an example, not an included component; consult its upstream license and distribution guidance before considering bundling or modification. Do not assume MIT covers it.

Audio recordings and reference transcripts need their own permission/license. Personal meeting recordings and transcripts must not be committed. Use synthetic fixtures or explicitly licensed media and retain attribution when required. Brand identity availability remains unconfirmed independently of copyright licensing of the original SVG files.


## Capture milestone dependency inventory

Installed metadata inspected on 2026-10-28; this inventory records the local tested environment, not a claim that every allowed version has identical terms:

| Package | Local version | License in installed metadata |
| --- | --- | --- |
| Typer | 0.27.3 | MIT |
| Rich | 14.3.4 | MIT |
| SoundCard | 0.4.6 | BSD 3-clause |
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| CFFI (SoundCard dependency) | 2.1.1 | MIT-0 |

Native system audio libraries are loaded from the operating system. Azure SDK and resampler dependencies were added in the translation milestone; GUI dependencies remain deferred. Redistributing dependencies/binaries requires retaining their actual notices; this summary does not replace those notices.


## Translation milestone additions

Installed artifacts inspected on 2026-10-28:

| Package | Local version | Terms/notices |
| --- | --- | --- |
| Azure Cognitive Services Speech SDK | 1.53.0 | Microsoft SDK license (`LICENSE.md`), `REDIST.txt`, and `ThirdPartyNotices.md` shipped in its installed distribution; not MIT |
| python-soxr | 1.1.0 | Installed metadata: LGPL-2.1-or-later; review native libsoxr notices before binary redistribution |
| azure-core (SDK dependency) | 1.41.0 | Retain its version-specific upstream license/notices when redistributing |

Liltide depends on these packages through normal installation; its own wheel does not bundle SDK or resampler binaries. Their terms remain independent of Liltide's MIT license. Future standalone installers must include a full transitive/native notice inventory and comply with the selected components' redistribution terms. No GUI library has been installed.
