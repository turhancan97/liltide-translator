"""Caption timing aggregates. Source-end delay is explicitly an estimate."""

import math
from statistics import median


def distribution(values):
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "median_ms": median(ordered) if ordered else None,
        "p95_ms": ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None,
        "min_ms": ordered[0] if ordered else None,
        "max_ms": ordered[-1] if ordered else None,
    }


def timing_summary(captions):
    finals = [event for event in captions if event.final]
    estimates = [e.estimated_final_delay_ms for e in finals if e.estimated_final_delay_ms is not None]
    return {
        "final_captions": len(finals),
        "translated_final_captions": sum(bool((e.english or "").strip()) for e in finals),
        "provider_callback_captions": sum(e.timing_source == "provider_callback" for e in finals),
        "handler_only_captions": sum(e.timing_source == "session_handler" for e in finals),
        "negative_estimates": sum(v < 0 for v in estimates),
        "estimated_final_delay": distribution(estimates),
        "dispatch_delay": distribution(e.dispatch_delay_ms for e in finals if e.dispatch_delay_ms is not None),
        "provisional_to_final": distribution(e.provisional_to_final_ms for e in finals if e.provisional_to_final_ms is not None),
    }
