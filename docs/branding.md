# Liltide branding

Status: user-approved palette revision, 2026-10-29; supersedes the original teal palette. Name availability remains unconfirmed.

## Identity and voice

**Liltide** — **Live captions across languages.**

A calm, practical tool for following lectures across language barriers. Polish-to-English is the first planned pair; the name and tagline allow future expansion without promising it today. Use `Liltide` in prose and `liltide` for the command/package identifier.

Write in clear, concise English. Use “Polish transcript,” “English translation,” “provisional,” and “finalized” consistently. Finalized means the provider has committed a segment, not that its contents are guaranteed correct. Use “planned” until implemented, and “verified” only with recorded evidence. Avoid “perfect,” “instant,” and unsupported privacy or performance promises.

Preliminary web searches during planning found no obvious exact-name software conflict. This is not package reservation, domain availability, or trademark clearance. Recheck before public distribution; do not register or purchase anything automatically.

## Color and typography

| Token | Hex | Intended use |
| --- | --- | --- |
| Signal blue | `#3a7eab` | Primary identity, speech waveform, large headings, graphic accents on white or dark ink |
| Translation red | `#cf4832` | Secondary identity, flowing translation wave, small accent markers |
| Neutral gray | `#d1d3d4` | Neutral surfaces, decorative separators, text on dark ink |
| Ink (supporting neutral) | `#17212b` | Body text on white/gray and dark-theme background |
| White (supporting neutral) | `#ffffff` | Light-theme background and monochrome inverse assets |

The three brand colors above are the user's exact selections. Ink and white support readable text and light/dark presentation; they are not replacements for the chosen palette. Machine-readable values are in [colors.json](../assets/brand/colors.json).

Use system sans-serif for prose/UI and system monospace for CLI examples. The SVG wordmark uses a system sans-serif font stack; exact letterforms can vary by installed font. No font files are bundled.

Text must meet WCAG AA contrast: 4.5:1 for normal text and 3:1 for large text; meaningful UI graphics need 3:1 against adjacent colors. The [current contrast record](validation.md#brand-refresh--2026-10-29) lists measured pairs. Blue on white is **4.42:1**: approved for large text and graphics, not normal text. Use ink for small text on white or gray, and gray/white for small text on ink. Red on white meets normal text at **4.54:1**, but has little margin; do not reduce opacity. Neither blue nor red is approved for normal text on gray or ink. Blue on gray also falls below 3:1 for meaningful graphics; put a blue icon on a white/ink surface instead. Gray-on-white borders are decorative only; use blue/red/ink when a boundary communicates information.

Red is a brand accent, not an error state by itself. Pair every state with a word or icon; do not imply that the translation language is an error. No new terminal colors are forced because terminal backgrounds vary.

The GUI defaults to System theme, with Light/Dark manual overrides. Terminal output respects `NO_COLOR`, `TERM=dumb`, and non-interactive output. Never use color as the sole indication of errors, provisional text, recording state, or connection status.

## Logo assets

The continuous waveform rises and falls in blue, then flows into a red wave: speech becoming a continuous stream of captions. Both colored variants use the same blue/red symbol; dark mode uses a gray wordmark. It is an original vector mark without third-party icons or embedded images.

| Variant | Symbol | Horizontal wordmark | Surface |
| --- | --- | --- | --- |
| Light | [SVG](../assets/brand/liltide-symbol-light.svg) | [SVG](../assets/brand/liltide-wordmark-light.svg) | Light/white |
| Dark | [SVG](../assets/brand/liltide-symbol-dark.svg) | [SVG](../assets/brand/liltide-wordmark-dark.svg) | Ink/dark |
| Mono black | [SVG](../assets/brand/liltide-symbol-mono-black.svg) | [SVG](../assets/brand/liltide-wordmark-mono-black.svg) | Light/white |
| Mono white | [SVG](../assets/brand/liltide-symbol-mono-white.svg) | [SVG](../assets/brand/liltide-wordmark-mono-white.svg) | Ink/black |

See the [rendered contact sheet](../assets/brand/preview.png) for all variants and tested sizes.

## Redesigned components

- README banners: [light](../assets/brand/liltide-banner-light.svg) and [dark](../assets/brand/liltide-banner-dark.svg), with matching 1100×320 layout, original waveform, tagline, paired caption-line motif, and “POLISH → ENGLISH · CLI + DESKTOP” label. Light uses white/ink; dark uses ink/gray; both retain the exact blue/red accents. The [original filename](../assets/brand/liltide-banner.svg) is an identical light fallback for existing references.
- The README uses GitHub's documented [`picture` pattern](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github#adding-an-image-to-suit-your-visitors) with `prefers-color-scheme` sources and descriptive fallback alt text. Selection follows the browser's reported color-scheme preference; individual Markdown viewers may ignore this HTML or show only the fallback. Actual GitHub theme rendering remains to be checked after publication. No embedded SVG scripts, remote fonts, or external image resources.
- [Brand board SVG](../assets/brand/brand-board.svg) and [PNG preview](../assets/brand/brand-board.png): exact palette swatches, light/dark wordmarks, and two caption cards.
- Caption cards are labeled **Concept — not implemented**, use synthetic text, and demonstrate accessible finalized/provisional labels. They do not represent a shipped GUI or change the current terminal interface.

## Asset usage

Logo symbol and wordmark SVGs have transparent backgrounds, accessible titles/descriptions, and fixed colors. The banner and brand board use explicit background surfaces. Select the correct variant; a white mark on white will be invisible. Keep aspect ratio and allow clear space of at least one stroke-width around the mark. Minimum intended sizes: symbol 24 px square; wordmark 160 px wide. Use the symbol alone below the wordmark minimum; a 16 px symbol is exploratory and not approved as an application icon.

Do not stretch, rotate, add gradients/shadows, or place the logo on low-contrast photographs. Use the monochrome variants for one-color reproduction. MIT applies to these original assets; no third-party brand endorsement is implied.

## Screenshots and terminal presentation

Use synthetic Polish/English examples with elapsed timestamps. Never capture credentials, private meetings, or personal audio-device names. Label every unimplemented interface mockup “Concept — not implemented.” Later screenshots must identify the version and platform and show the actual interface. Keep the original audio experience uninterrupted where routing permits it; do not imply audio capture is active while paused.

## Implemented desktop styling — 2026-10-29

The Python GUI now reuses the original waveform symbol and exact blue/red/gray palette, with ink/white readable surfaces. Blue outlines identify Start/state accents; red accents identify Stop, provisional text, and focus without replacing words. Normal text is ink on white or white/gray on ink; selection uses ink on gray. Blue is not used for small text or white-on-blue button labels (that pair is only 4.42:1). Focus/accent graphics on white/ink meet 3:1. Checked controls have an explicit checkmark and boundary rather than color alone.

The shipped symbol at `src/liltide/resources/symbol.svg` is an unchanged packaged copy of the canonical light SVG; keep both synchronized. `check.svg` is an original utility mark, not a replacement logo. System fonts and a 16 pt default caption size support the grouped/resizable layout. Light/dark themes and compact sizing were visually inspected offscreen; live OS theme and assistive-technology validation remain open. The earlier caption-card concepts remain labeled concepts and are not screenshots of this implementation.

## Repository social preview

Upload [liltide-social-preview.png](../assets/brand/liltide-social-preview.png) for the repository social preview. The editable [SVG master](../assets/brand/liltide-social-preview.svg) uses the original waveform, approved palette, tagline, Polish-to-English positioning and CLI/desktop label. The PNG is 1280×640, opaque RGB, and under 1 MB, following [GitHub's social-preview guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview) checked 2026-10-30. A solid ink background keeps the card consistent across sharing platforms; it does not switch with the viewer's theme. No third-party icons, remote fonts or embedded screenshots are used.

Render with `rsvg-convert -o assets/brand/liltide-social-preview.png assets/brand/liltide-social-preview.svg`. Text rasterization can vary by installed system font. Previewed at full size and 640×320; retain generous margins and clear primary text when revising. Uploading/configuring the image on GitHub is a separate action; creating the asset does not set the repository's social preview.
