"""Generate docs/polygon_coverage.md from polygon_coverage_priority.csv.

Companion to `scripts/audit_polygon_coverage.py`:
  audit_polygon_coverage    → produces the CSV (per-site rows)
  generate_polygon_coverage_md → renders the CSV as a markdown doc

The doc is git-readable so reviewers can scan polygon coverage without
opening the CSV. It surfaces the cumulative demand-share lever (so we
can tell when remaining uncovered sites stop being worth hunting).

Run:
    PYTHONPATH=. uv run python scripts/audit_polygon_coverage.py
    PYTHONPATH=. uv run python scripts/generate_polygon_coverage_md.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "outputs" / "data" / "processed" / "polygon_coverage_priority.csv"
OUTPUT = REPO_ROOT / "docs" / "polygon_coverage.md"
TOP_N_LEVER = 15
MWH_PER_TWH = 1e6  # 1 TWh = 1,000,000 MWh; thresholds switch demand units


def fmt_demand(v: float) -> str:
    if pd.isna(v):
        return "—"
    if v >= MWH_PER_TWH:
        return f"{v / MWH_PER_TWH:.1f} TWh"
    return f"{v / 1e3:.0f} GWh"


def polygon_kind(row: pd.Series) -> str:
    if row["has_kek_polygon"]:
        return "KEK"
    if row["has_industrial_polygon"]:
        return "industrial"
    return "—"


def main() -> int:
    df = pd.read_csv(INPUT)

    total_demand = df["demand_proxy_mwh"].sum()
    covered_demand = df[df["effective_polygon_coverage"]]["demand_proxy_mwh"].sum()
    uncovered_demand = df[~df["effective_polygon_coverage"]]["demand_proxy_mwh"].sum()
    n_total = len(df)
    n_covered = int(df["effective_polygon_coverage"].sum())

    unc = df[~df["effective_polygon_coverage"]].copy()
    unc = unc.sort_values("demand_proxy_mwh", ascending=False, na_position="last")
    unc["cum_demand_mwh"] = unc["demand_proxy_mwh"].cumsum()
    unc["cum_pct_of_total"] = unc["cum_demand_mwh"] / total_demand * 100

    cov = df[df["effective_polygon_coverage"]].sort_values(
        "demand_proxy_mwh", ascending=False, na_position="last"
    )

    lines: list[str] = []
    lines.append("# Polygon coverage by site\n")
    lines.append("Auto-generated. Regenerate via:\n")
    lines.append(
        "```bash\n"
        "PYTHONPATH=. uv run python scripts/audit_polygon_coverage.py\n"
        "PYTHONPATH=. uv run python scripts/generate_polygon_coverage_md.py\n"
        "```\n"
    )
    lines.append(f"**Source:** `{INPUT.relative_to(REPO_ROOT)}`\n")

    lines.append("\n## Summary\n")
    lines.append(f"- **Sites covered:** {n_covered} / {n_total} ({n_covered / n_total * 100:.0f}%)")
    lines.append(f"  - KEK polygons: {int(df['has_kek_polygon'].sum())} / 25")
    lines.append(f"  - Industrial polygons: {int(df['has_industrial_polygon'].sum())} / 56")
    lines.append(
        f"- **Demand covered:** {covered_demand / 1e6:,.1f} TWh / "
        f"{total_demand / 1e6:,.1f} TWh "
        f"(**{covered_demand / total_demand * 100:.1f}%**)"
    )
    lines.append(
        f"- **Demand uncovered:** {uncovered_demand / 1e6:,.1f} TWh "
        f"({uncovered_demand / total_demand * 100:.1f}%)\n"
    )
    lines.append(
        "Demand is `capacity_annual_tonnes × SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` "
        "for industrial sites and `area_ha × intensity_per_ha` for KEKs (same formula "
        "`fct_site_demand` uses). NaN-demand rows excluded from totals.\n"
    )

    lines.append("## Marginal lever — top uncovered sites by cumulative demand share\n")
    lines.append("Add a polygon to these in order, biggest impact first.\n")
    lines.append("| # | Site | Sector | Demand | Cumulative % of total |")
    lines.append("|---|------|--------|--------|-----------------------|")
    for i, (_, r) in enumerate(unc.head(TOP_N_LEVER).iterrows(), 1):
        name = r["site_name"][:50]
        sector = r["sector"] if pd.notna(r["sector"]) else "—"
        lines.append(
            f"| {i} | {name} | {sector} | {fmt_demand(r['demand_proxy_mwh'])} | "
            f"{r['cum_pct_of_total']:.1f}% |"
        )
    lines.append("")
    lines.append("After the top 5, marginal lift drops below 1 percentage point per site.\n")

    def render_table(rows: pd.DataFrame, title: str) -> None:
        lines.append(f"## {title}\n")
        lines.append("| Site | Sector | Type | Polygon | Demand | Rooftop MWp |")
        lines.append("|------|--------|------|---------|--------|-------------|")
        for _, r in rows.iterrows():
            name = r["site_name"][:55]
            sector = r["sector"] if pd.notna(r["sector"]) else "—"
            st = r["site_type"] if pd.notna(r["site_type"]) else "—"
            roof = (
                f"{r['rooftop_solar_mwp_potential']:.1f}"
                if pd.notna(r["rooftop_solar_mwp_potential"])
                else "—"
            )
            lines.append(
                f"| {name} | {sector} | {st} | {polygon_kind(r)} | "
                f"{fmt_demand(r['demand_proxy_mwh'])} | {roof} |"
            )
        lines.append("")

    render_table(cov, f"Covered ({n_covered} sites)")
    render_table(unc, f"Uncovered ({n_total - n_covered} sites — sorted by demand)")

    OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
