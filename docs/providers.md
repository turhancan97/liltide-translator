# Provider comparison and free-only policy

Official documentation reviewed: **2026-10-28**. No account access, API calls, or comparative accuracy benchmarks were performed. Prices, allowances, and access conditions can change; recheck before live use.

| Candidate | Integration shape | Published free offer | Fit for initial scope |
| --- | --- | --- | --- |
| Azure Speech F0 | Combined continuous recognition and translation, including intermediate/final results | Speech translation: 5 audio hours/month on F0 | Selected: one integration and a recurring free translation allowance |
| Google Speech V1 + Cloud Translation NMT | Streaming transcription plus a separate text translation integration | Speech V1: 60 minutes/month; NMT: first 500,000 characters/month | Alternative; separate quotas and billing-enabled configuration require additional controls |
| Deepgram transcription + separate translator | Streaming recognition followed by another translation service | Introductory $200 transcription credit, rather than a recurring translation allowance | Not selected: transcription credit alone does not cover an end-to-end translation pipeline |

Sources: [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/speech/), [continuous/intermediate Azure translation](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-translate-speech?pivots=programming-language-python), [Azure language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support), [Google speech pricing](https://cloud.google.com/speech-to-text/pricing), [Google translation pricing](https://cloud.google.com/products/translate/pricing), [Google billing setup](https://docs.cloud.google.com/speech-to-text/docs/setup), and [Deepgram pricing](https://deepgram.com/pricing).

The Google speech allowance here refers to V1, not a general promise about V2. Introductory credits are not treated as permission to incur charges. Provider marketing claims are not evidence of Polish recognition or translation quality in Liltide.

## Selected policy

- Azure Speech **F0 only** for the first provider. Polish source `pl-PL`, English target `en`. One active session initially; Azure documents an F0 concurrent-request limit of one for the applicable real-time recognition/translation category. See [Azure quotas](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits).
- Use continuous translation events for both transcript and translation. Do not add a separately billed translation service by default.
- Confirm the actual resource SKU manually before live use. Never create paid resources, silently select S0, upgrade a tier, or switch providers/resources automatically after rejection.
- Stop on confirmed quota exhaustion. Explain transient rate limits separately where the service exposes enough information; do not fabricate a diagnosis from a generic cancellation.
- Any local session-duration display is an estimate, not an account-wide allowance tracker. Other clients may consume the same resource, and SDK credentials alone cannot prove SKU or remaining quota.
- Free-only is a resource-configuration requirement plus a no-fallback application policy. Liltide cannot guarantee zero billing on a misconfigured or externally changed account.
- No shared embedded key, hosted relay, or Liltide account. Users supply their own resource credentials. Never run cloud tests automatically in CI.

## Decision rationale and revisit conditions

Azure offers the smallest initial integration for the approved behavior and recurring free-only constraint. This is an engineering choice, not a measured quality ranking. Revisit only with user approval if F0 cannot be used, representative Polish translation is inadequate, compatibility prevents support, or the product requirements change. Exhausting a free allowance alone must not trigger an automatic paid migration.
