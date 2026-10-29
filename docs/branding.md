# Liltide branding

Status: approved direction; assets created for the documentation milestone. Name availability remains unconfirmed.

## Identity and voice

**Liltide** — **Live captions across languages.**

A calm, practical tool for following lectures across language barriers. Polish-to-English is the first planned pair; the name and tagline allow future expansion without promising it today. Use `Liltide` in prose and `liltide` for the command/package identifier.

Write in clear, concise English. Use “Polish transcript,” “English translation,” “provisional,” and “finalized” consistently. Finalized means the provider has committed a segment, not that its contents are guaranteed correct. Use “planned” until implemented, and “verified” only with recorded evidence. Avoid “perfect,” “instant,” and unsupported privacy or performance promises.

Preliminary web searches during planning found no obvious exact-name software conflict. This is not package reservation, domain availability, or trademark clearance. Recheck before public distribution; do not register or purchase anything automatically.

## Color and typography

| Token | Hex | Intended use |
| --- | --- | --- |
| Deep teal | `#0F766E` | Accent/text on light surfaces |
| Bright teal | `#2DD4BF` | Accent/text on dark surfaces |
| Slate | `#0F172A` | Main text on light; dark background |
| Light | `#F8FAFC` | Light background; main text on dark |
| Muted gray | `#64748B` | Secondary text on light only, subject to contrast |

Use system sans-serif for prose/UI and system monospace for CLI examples. The SVG wordmark uses a system sans-serif font stack; exact letterforms can vary by installed font. No font files are bundled.

Text must meet WCAG AA contrast: 4.5:1 for normal text and 3:1 for large text; meaningful UI graphics need 3:1 against adjacent colors. Check actual combinations, not colors in isolation. The [validation record](validation.md) lists approved pairs. Bright teal on light and deep teal on slate are not approved text combinations. Use light text rather than muted gray for secondary text on slate unless a new compliant color is introduced.

Follow the system theme in the future GUI, with a manual override. Terminal output respects `NO_COLOR`, `TERM=dumb`, and non-interactive output. Never use color as the sole indication of errors, provisional text, recording state, or connection status.

## Logo assets

The continuous waveform rises and falls, then flows into a smooth wave: speech becoming a continuous stream of captions. It is an original vector mark without third-party icons or embedded images.

| Variant | Symbol | Horizontal wordmark | Surface |
| --- | --- | --- | --- |
| Light | [SVG](../assets/brand/liltide-symbol-light.svg) | [SVG](../assets/brand/liltide-wordmark-light.svg) | Light/white |
| Dark | [SVG](../assets/brand/liltide-symbol-dark.svg) | [SVG](../assets/brand/liltide-wordmark-dark.svg) | Slate/dark |
| Mono black | [SVG](../assets/brand/liltide-symbol-mono-black.svg) | [SVG](../assets/brand/liltide-wordmark-mono-black.svg) | Light/white |
| Mono white | [SVG](../assets/brand/liltide-symbol-mono-white.svg) | [SVG](../assets/brand/liltide-wordmark-mono-white.svg) | Slate/black |

See the [rendered contact sheet](../assets/brand/preview.png) for all variants and tested sizes.

All SVGs have transparent backgrounds, accessible titles/descriptions, and fixed colors. Select the correct variant; a white mark on white will be invisible. Keep aspect ratio and allow clear space of at least one stroke-width around the mark. Minimum intended sizes: symbol 24 px square; wordmark 160 px wide. Use the symbol alone below the wordmark minimum; a 16 px symbol is exploratory and not approved as an application icon.

Do not stretch, rotate, add gradients/shadows, or place the logo on low-contrast photographs. Use the monochrome variants for one-color reproduction. MIT applies to these original assets; no third-party brand endorsement is implied.

## Screenshots and terminal presentation

Use synthetic Polish/English examples with elapsed timestamps. Never capture credentials, private meetings, or personal audio-device names. Until the app exists, label any mockup “Concept — not implemented.” Later screenshots must identify the version and platform and show the actual interface. Keep the original audio experience uninterrupted where routing permits it; do not imply audio capture is active while paused.
