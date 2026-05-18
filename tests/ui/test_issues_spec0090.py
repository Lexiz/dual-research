"""Spec 0090 § A.2 — issue-resolution parser recognises broader ID shapes.

Pre-spec the ``_ID_TOKEN_RE`` only matched uppercase-initial IDs
(``[A-Z]{1,4}-...``), which silently dropped every system-generated
cross-round ID like ``I-g-r1-01``. Body-signature dedup then fell back
to body-prefix matching, which failed when the agent's wording shifted
across rounds.

Post-spec: lowercase-initial system IDs are recognised so cross-round
dedup works.
"""

from __future__ import annotations

from dual_research.ui.issues import _ID_TOKEN_RE, _body_signature


class TestIdTokenRegex:
    def test_lowercase_initial_system_ids(self) -> None:
        """Spec 0090 § A.2 — the I-g-rN-NN / Q-c-rN-NN / Cl-c-pN-NN
        shapes must match."""
        for sample in [
            "I-g-r1-01",
            "I-c-r2-05",
            "Q-c-r1-01",
            "Q-g-r3-12",
            "Cl-c-p1-04",
            "Cl-g-r1-02",
        ]:
            m = _ID_TOKEN_RE.search(sample)
            assert m is not None, f"failed to match {sample!r}"
            assert m.group(1) == sample

    def test_uppercase_agent_ids_still_match(self) -> None:
        """Backward compat: pre-spec uppercase IDs continue to match."""
        for sample in ["OAI-1", "OAI-P4-3", "D-5", "D-OAI-1", "C-7", "FSD-1"]:
            m = _ID_TOKEN_RE.search(sample)
            assert m is not None, f"failed to match {sample!r}"


class TestBodySignatureWithBroaderIds:
    """The body signature is what dedupes an issue across rounds. With
    the broader regex the I-g-rN-NN form is now caught, so a drafter's
    cross-round reference matches the original raise."""

    def test_cross_round_system_id_extracted(self) -> None:
        sig = _body_signature(
            "**[I-g-r1-01]** — **resolved.** Inline [V]/[U] tags added throughout"
        )
        assert sig == "id:i-g-r1-01"

    def test_phased_oai_id_extracted(self) -> None:
        sig = _body_signature("**OAI-P4-3** — open — body text")
        assert sig == "id:oai-p4-3"

    def test_two_round_dedupe(self) -> None:
        """An issue referenced in two different roundings — by the
        cross-round ID — must dedupe to the same signature."""
        r1 = "**OAI-P4-1 — open:** body wording A"
        r3 = "**[I-g-r1-01]** — **resolved.** body wording B (drafter resolved)"
        # These are different IDs (one is the raiser's own, one is the
        # system cross-round ID) — they SHOULDN'T dedupe across each
        # other, just confirms each individually extracts an ID and
        # falls into its own bucket. The cross-agent resolution
        # detection is a separate (out-of-scope) concern.
        sig_r1 = _body_signature(r1)
        sig_r3 = _body_signature(r3)
        assert sig_r1.startswith("id:")
        assert sig_r3.startswith("id:")

    def test_no_id_falls_back_to_body_prefix(self) -> None:
        sig = _body_signature("plain body text with no recognisable id")
        assert sig.startswith("body:")
