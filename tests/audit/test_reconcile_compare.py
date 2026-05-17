"""Spec 0048 — compare_day pure-function tests for the 5-state status machine."""

from __future__ import annotations

from dual_research.audit.reconcile import compare_day


def _local(provider: str, model: str, usd: float) -> dict:
    return {(provider, model): {"usd": usd, "run_ids": ["r-1"], "pricing_versions": ["2026-05-17"]}}


CHECKED_AT = "2026-05-17T12:00:00Z"


class TestVerificationStatus:
    def test_unverified_when_no_provider_keys(self):
        r = compare_day(
            date="2026-05-16",
            local_day=_local("openai", "gpt-5.5", 5.0),
            anthropic_day=None,
            openai_day=None,
            providers_skipped={
                "anthropic": "ANTHROPIC_ADMIN_KEY not set",
                "openai": "OPENAI_ADMIN_KEY not set",
            },
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.verification_status == "unverified"
        assert r.providers_checked == []
        assert r.total_local_usd == 5.0  # local-only total still surfaces

    def test_verified_when_both_within_tolerance(self):
        r = compare_day(
            date="2026-05-16",
            local_day={
                ("anthropic", "claude-sonnet-4-6"): {"usd": 5.00, "run_ids": ["r"], "pricing_versions": []},
                ("openai", "gpt-5.5"): {"usd": 3.00, "run_ids": ["r"], "pricing_versions": []},
            },
            anthropic_day={"claude-sonnet-4-6": 5.00},
            openai_day={"gpt-5.5": 3.00},
            providers_skipped={},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.verification_status == "verified"
        assert r.total_delta_usd == 0.0

    def test_drift_when_any_row_exceeds_tolerance(self):
        r = compare_day(
            date="2026-05-16",
            local_day={("openai", "gpt-5.5"): {"usd": 1.00, "run_ids": ["r"], "pricing_versions": []}},
            anthropic_day={},
            openai_day={"gpt-5.5": 10.00},  # 9x over local — definitely flagged
            providers_skipped={},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.verification_status == "drift"
        assert any(d.flagged for d in r.per_model_deltas)

    def test_partial_when_one_provider_skipped(self):
        r = compare_day(
            date="2026-05-16",
            local_day={
                ("anthropic", "claude-sonnet-4-6"): {"usd": 5.00, "run_ids": ["r"], "pricing_versions": []},
                ("openai", "gpt-5.5"): {"usd": 3.00, "run_ids": ["r"], "pricing_versions": []},
            },
            anthropic_day=None,                  # Anthropic skipped
            openai_day={"gpt-5.5": 3.00},        # OpenAI checked + matches
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.verification_status == "partial"
        assert r.providers_checked == ["openai"]
        assert "anthropic" in r.providers_skipped

    def test_awaiting_provider_data_when_provider_returned_empty(self):
        r = compare_day(
            date="2026-05-16",
            local_day=_local("openai", "gpt-5.5", 5.0),
            anthropic_day=None,
            openai_day={},  # key set, fetcher ran, but bucket was empty
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.verification_status == "awaiting_provider_data"


class TestPerRowDeltas:
    def test_local_only_row_has_zero_provider_and_no_flag(self):
        """A (provider, model) that exists locally but not in provider data
        means the provider didn't bill us for it on this day — surfaces as
        a row with provider_usd=0, but NOT flagged (delta is meaningful
        only against non-zero provider totals)."""
        r = compare_day(
            date="2026-05-16",
            local_day=_local("openai", "gpt-5.5", 5.0),
            anthropic_day={},
            openai_day={},  # provider didn't bill for gpt-5.5
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        # Note: openai_day={} → awaiting status (no data at all). For per-row
        # behavior we need openai_day to be truthy. Try a different angle:
        r2 = compare_day(
            date="2026-05-16",
            local_day={
                ("openai", "gpt-5.5"): {"usd": 5.00, "run_ids": ["r"], "pricing_versions": []},
                ("openai", "gpt-4.1"): {"usd": 1.00, "run_ids": ["r"], "pricing_versions": []},
            },
            anthropic_day={},
            openai_day={"gpt-5.5": 5.00},  # gpt-4.1 missing from provider
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        gpt41 = next(d for d in r2.per_model_deltas if d.model_id == "gpt-4.1")
        assert gpt41.provider_usd == 0.0
        assert gpt41.flagged is False

    def test_delta_pct_calculation(self):
        r = compare_day(
            date="2026-05-16",
            local_day={("openai", "gpt-5.5"): {"usd": 10.00, "run_ids": ["r"], "pricing_versions": []}},
            anthropic_day={},
            openai_day={"gpt-5.5": 11.00},
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=5.0,
            checked_at=CHECKED_AT,
        )
        d = r.per_model_deltas[0]
        assert d.delta_usd == -1.00         # local - provider
        assert abs(d.delta_pct - (1.0 / 11.0) * 100) < 1e-3
        # 1/11 * 100 = 9.09% > 5% tolerance → flagged
        assert d.flagged is True

    def test_tolerance_threshold_inclusive_at_zero(self):
        """Exact match (delta=0) is never flagged regardless of tolerance."""
        r = compare_day(
            date="2026-05-16",
            local_day={("openai", "gpt-5.5"): {"usd": 5.00, "run_ids": ["r"], "pricing_versions": []}},
            anthropic_day={},
            openai_day={"gpt-5.5": 5.00},
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=0.0,
            checked_at=CHECKED_AT,
        )
        d = r.per_model_deltas[0]
        assert d.flagged is False


class TestAggregateBehaviour:
    def test_total_local_includes_unverified_providers(self):
        """When only OpenAI is checked, the report's total_local_usd
        should still include the Anthropic-side local spend (so users see
        the full picture of what their account spent, even partially-
        verified)."""
        r = compare_day(
            date="2026-05-16",
            local_day={
                ("anthropic", "claude-sonnet-4-6"): {"usd": 7.00, "run_ids": ["r"], "pricing_versions": []},
                ("openai", "gpt-5.5"): {"usd": 3.00, "run_ids": ["r"], "pricing_versions": []},
            },
            anthropic_day=None,
            openai_day={"gpt-5.5": 3.00},
            providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
            tolerance_pct=1.0,
            checked_at=CHECKED_AT,
        )
        assert r.total_local_usd == 10.0   # both providers' local spend
        assert r.total_provider_usd == 3.0  # only OpenAI was verified
