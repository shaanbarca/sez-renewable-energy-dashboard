"""Tests for src/utils/provenance.py — field-level data provenance.

Pins the foundation (#65 v4.1a) so downstream sub-PRs (#67-72) that extend
`PROVENANCE_REGISTRY` can rely on the schema and constructor invariants.
"""

from __future__ import annotations

import pytest

from src.utils.provenance import (
    PROVENANCE_REGISTRY,
    ProvenanceFlag,
    build_sidecar_rows,
)


class TestProvenanceFlag:
    def test_construct_valid(self) -> None:
        pf = ProvenanceFlag(
            source="Global Solar Atlas v2",
            vintage="2020",
            confidence="high",
            citation="World Bank ESMAP / Solargis 2020",
        )
        assert pf.source == "Global Solar Atlas v2"
        assert pf.vintage == "2020"
        assert pf.confidence == "high"
        assert pf.citation == "World Bank ESMAP / Solargis 2020"

    def test_frozen_immutable(self) -> None:
        """`@dataclass(frozen=True)` — registry entries must not be mutated after
        construction. Per-site overrides return new ProvenanceFlag instances."""
        pf = ProvenanceFlag(source="s", vintage="v", confidence="high", citation="c")
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            pf.confidence = "low"  # type: ignore[misc]

    @pytest.mark.parametrize("bad_confidence", ["HIGH", "med", "unknown", "", "1", "high "])
    def test_invalid_confidence_raises(self, bad_confidence: str) -> None:
        with pytest.raises(ValueError, match="confidence"):
            ProvenanceFlag(
                source="s",
                vintage="v",
                confidence=bad_confidence,  # type: ignore[arg-type]
                citation="c",
            )

    @pytest.mark.parametrize("field", ["source", "vintage", "citation"])
    def test_empty_string_raises(self, field: str) -> None:
        """Empty strings for source/vintage/citation are caught at construction
        time. Prevents a registry entry from silently emitting blank provenance."""
        kwargs = {
            "source": "s",
            "vintage": "v",
            "confidence": "high",
            "citation": "c",
            field: "",
        }
        with pytest.raises(ValueError, match=field):
            ProvenanceFlag(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("confidence", ["high", "medium", "low"])
    def test_all_three_confidence_levels_accepted(self, confidence: str) -> None:
        pf = ProvenanceFlag(
            source="s",
            vintage="v",
            confidence=confidence,  # type: ignore[arg-type]
            citation="c",
        )
        assert pf.confidence == confidence


class TestProvenanceRegistry:
    def test_seed_registry_has_three_v40_fields(self) -> None:
        """v4.1a foundation seed: pvout, bpp, industrial tariff. Pins so
        downstream sub-PRs don't accidentally remove an existing entry."""
        expected = {
            "pvout_centroid_kwh_kwp_yr",
            "bpp_usd_mwh",
            "industrial_tariff_usd_mwh",
        }
        assert expected.issubset(PROVENANCE_REGISTRY.keys())

    def test_every_registry_entry_constructs_cleanly(self) -> None:
        """The registry is dataclass-validated at import time, but pin it
        explicitly so a future bad entry surfaces in CI rather than at runtime."""
        for field_name, (flag, _override) in PROVENANCE_REGISTRY.items():
            assert isinstance(flag, ProvenanceFlag), f"{field_name}: not a ProvenanceFlag"
            assert flag.confidence in ("high", "medium", "low"), (
                f"{field_name}: invalid confidence {flag.confidence!r}"
            )
            assert flag.source and flag.vintage and flag.citation, (
                f"{field_name}: blank field in default ProvenanceFlag"
            )


class TestBuildSidecarRows:
    def test_empty_site_list_returns_no_rows(self) -> None:
        assert build_sidecar_rows([]) == []

    def test_three_sites_three_fields_makes_nine_rows(self) -> None:
        rows = build_sidecar_rows(["site-a", "site-b", "site-c"])
        # 3 sites × 3 default-registry fields = 9 rows.
        # If downstream sub-PRs add fields to PROVENANCE_REGISTRY this test
        # would need updating — that's the point, it pins the foundation seed.
        assert len(rows) == 3 * len(PROVENANCE_REGISTRY)

    def test_row_schema(self) -> None:
        rows = build_sidecar_rows(["kek-palu"])
        assert rows  # non-empty
        first = rows[0]
        assert set(first.keys()) == {
            "site_id",
            "field_name",
            "source",
            "vintage",
            "confidence",
            "citation",
        }
        assert first["site_id"] == "kek-palu"

    def test_override_loader_returns_per_site_provenance(self) -> None:
        # Custom registry: one field with a per-site override that bumps
        # confidence to "low" for site-b.
        custom_flag = ProvenanceFlag(
            source="default_source",
            vintage="2024",
            confidence="high",
            citation="default citation",
        )
        site_b_flag = ProvenanceFlag(
            source="override_source",
            vintage="2024",
            confidence="low",
            citation="site-b specific citation",
        )

        def loader(site_id: str) -> ProvenanceFlag | None:
            return site_b_flag if site_id == "site-b" else None

        rows = build_sidecar_rows(
            ["site-a", "site-b"],
            registry={"some_field": (custom_flag, loader)},
        )
        assert len(rows) == 2
        a = next(r for r in rows if r["site_id"] == "site-a")
        b = next(r for r in rows if r["site_id"] == "site-b")
        assert a["source"] == "default_source"
        assert a["confidence"] == "high"
        assert b["source"] == "override_source"
        assert b["confidence"] == "low"

    def test_override_loader_returning_none_uses_default(self) -> None:
        """Loader returning None for a site means 'use the default for this
        site' — does NOT mean 'omit this row'. (Omission is only when the
        loader explicitly returns a falsy flag that ALSO has no fallback,
        which the current build_sidecar_rows handles via the `or default`
        chain — both default and override-None route to the default flag.)"""
        custom_flag = ProvenanceFlag(
            source="default_source",
            vintage="2024",
            confidence="high",
            citation="default citation",
        )

        def loader(_: str) -> ProvenanceFlag | None:
            return None

        rows = build_sidecar_rows(["site-a"], registry={"some_field": (custom_flag, loader)})
        assert len(rows) == 1
        assert rows[0]["source"] == "default_source"

    def test_no_override_loader_means_default_for_all_sites(self) -> None:
        """`None` as the override loader is the common case — every site
        gets the default. Pin so the build step doesn't silently break it."""
        custom_flag = ProvenanceFlag(
            source="src", vintage="2024", confidence="high", citation="cite"
        )
        rows = build_sidecar_rows(
            ["site-a", "site-b"],
            registry={"some_field": (custom_flag, None)},
        )
        assert len(rows) == 2
        for r in rows:
            assert r["source"] == "src"


class TestFoundationSeed:
    """Pin the v4.1a foundation seed values so changing one is a deliberate
    decision (a downstream PR that updates the registry will need to update
    these tests, surfacing the change in code review)."""

    def test_pvout_provenance(self) -> None:
        flag, override = PROVENANCE_REGISTRY["pvout_centroid_kwh_kwp_yr"]
        assert override is None
        assert "Global Solar Atlas" in flag.source
        assert flag.confidence == "high"
        assert flag.vintage == "2020"

    def test_bpp_provenance(self) -> None:
        flag, override = PROVENANCE_REGISTRY["bpp_usd_mwh"]
        assert override is None
        assert "169" in flag.source  # Kepmen ESDM 169
        assert flag.confidence == "high"

    def test_industrial_tariff_provenance(self) -> None:
        flag, override = PROVENANCE_REGISTRY["industrial_tariff_usd_mwh"]
        assert override is None
        assert "Permen ESDM 7/2024" in flag.source
        assert flag.confidence == "high"
