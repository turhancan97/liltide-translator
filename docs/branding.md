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

Follow the system theme in the future GUI, with a manual override. Terminal output respects `NO_COLOR`, `TERM=dumb`, and non-interactive output. Never use color as the sole indication of errors, provisional text, recording state, or connection status.

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

- [README banner](../assets/brand/liltide-banner.svg): waveform/wordmark, tagline, and caption-line motif; used at the top of the README.
- [Brand board SVG](../assets/brand/brand-board.svg) and [PNG preview](../assets/brand/brand-board.png): exact palette swatches, light/dark wordmarks, and two caption cards.
- Caption cards are labeled **Concept — not implemented**, use synthetic text, and demonstrate accessible finalized/provisional labels. They do not represent a shipped GUI or change the current terminal interface.

## Asset usage

Logo symbol and wordmark SVGs have transparent backgrounds, accessible titles/descriptions, and fixed colors. The banner and brand board use explicit background surfaces. Select the correct variant; a white mark on white will be invisible. Keep aspect ratio and allow clear space of at least one stroke-width around the mark. Minimum intended sizes: symbol 24 px square; wordmark 160 px wide. Use the symbol alone below the wordmark minimum; a 16 px symbol is exploratory and not approved as an application icon.

Do not stretch, rotate, add gradients/shadows, or place the logo on low-contrast photographs. Use the monochrome variants for one-color reproduction. MIT applies to these original assets; no third-party brand endorsement is implied.

## Screenshots and terminal presentation

Use synthetic Polish/English examples with elapsed timestamps. Never capture credentials, private meetings, or personal audio-device names. Label every unimplemented interface mockup “Concept — not implemented.” Later screenshots must identify the version and platform and show the actual interface. Keep the original audio experience uninterrupted where routing permits it; do not imply audio capture is active while paused.
