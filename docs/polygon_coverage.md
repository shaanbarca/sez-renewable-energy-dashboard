# Polygon coverage by site

Auto-generated. Regenerate via:

```bash
PYTHONPATH=. uv run python scripts/audit_polygon_coverage.py
PYTHONPATH=. uv run python scripts/generate_polygon_coverage_md.py
```

**Source:** `outputs/data/processed/polygon_coverage_priority.csv`


## Summary

- **Sites covered:** 59 / 81 (73%)
  - KEK polygons: 25 / 25
  - Industrial polygons: 34 / 56
- **Demand covered:** 572.8 TWh / 662.4 TWh (**86.5%**)
- **Demand uncovered:** 89.6 TWh (13.5%)

Demand is `capacity_annual_tonnes × SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` for industrial sites and `area_ha × intensity_per_ha` for KEKs (same formula `fct_site_demand` uses). NaN-demand rows excluded from totals.

## Marginal lever — top uncovered sites by cumulative demand share

Add a polygon to these in order, biggest impact first.

| # | Site | Sector | Demand | Cumulative % of total |
|---|------|--------|--------|-----------------------|
| 1 | Nusantara Industri Sejati | nickel | 75.0 TWh | 11.3% |
| 2 | Inalum Asahan | aluminium | 3.8 TWh | 11.9% |
| 3 | Pupuk Kaltim Bontang | fertilizer | 2.4 TWh | 12.3% |
| 4 | Pupuk Sriwidjaja Palembang | fertilizer | 2.0 TWh | 12.6% |
| 5 | Buli Industrial Park | nickel | 1.5 TWh | 12.8% |
| 6 | Dexin Steel Morowali | steel | 1.4 TWh | 13.0% |
| 7 | SBI Narogong | cement | 667 GWh | 13.1% |
| 8 | Conch Cement North Sulawesi | cement | 484 GWh | 13.2% |
| 9 | Red Lion Hongshi Tonga | cement | 440 GWh | 13.2% |
| 10 | Indocement Kotabaru Tarjun | cement | 286 GWh | 13.3% |
| 11 | Semen Garuda Bekasi | cement | 275 GWh | 13.3% |
| 12 | Semen Grobogan | cement | 275 GWh | 13.4% |
| 13 | SBI Andalas Lhoknga | cement | 202 GWh | 13.4% |
| 14 | Semen Jawa SCG Sukabumi | cement | 198 GWh | 13.4% |
| 15 | Conch South Kalimantan | cement | 165 GWh | 13.4% |

After the top 5, marginal lift drops below 1 percentage point per site.

## Covered (59 sites)

| Site | Sector | Type | Polygon | Demand | Rooftop MWp |
|------|--------|------|---------|--------|-------------|
| Indonesia Morowali Industrial Park (IMIP) | nickel | cluster | industrial | 225.6 TWh | 75.1 |
| Indonesia Pomalaa Industry Park (IPIP) | nickel | cluster | industrial | 83.5 TWh | 12.3 |
| Virtue Dragon Nickel Industrial Park (VDNIP) | nickel | cluster | industrial | 75.0 TWh | 32.5 |
| Obi Island Industrial Park | nickel | cluster | industrial | 73.9 TWh | 0.0 |
| Industrial Weda Bay Industrial Park (IWIP) | nickel | cluster | industrial | 65.3 TWh | 0.0 |
| Bantaeng Industrial Park (BIP) | nickel | cluster | industrial | 9.9 TWh | 18.1 |
| Freeport Smelter Gresik | aluminium | standalone | industrial | 4.5 TWh | 2.8 |
| Petrokimia Gresik | fertilizer | standalone | industrial | 3.4 TWh | 68.5 |
| Krakatau Steel Cilegon | steel | standalone | industrial | 2.0 TWh | 87.5 |
| Industropolis Batang | mixed | kek | KEK | 1.9 TWh | 2.7 |
| Arun Lhokseumawe | mixed | kek | KEK | 1.8 TWh | 42.4 |
| Semen Gresik Tuban | cement | standalone | industrial | 1.6 TWh | 14.3 |
| Galang Batang | mixed | kek | KEK | 1.6 TWh | 6.7 |
| Gresik | mixed | kek | KEK | 1.5 TWh | 16.0 |
| Sei Mangkei | mixed | kek | KEK | 1.4 TWh | 6.5 |
| Indocement Citeureup | cement | standalone | industrial | 1.3 TWh | 63.5 |
| Pupuk Kujang Cikampek | fertilizer | standalone | industrial | 1.1 TWh | 11.0 |
| Pupuk Iskandar Muda Lhokseumawe | fertilizer | standalone | industrial | 1.1 TWh | 0.2 |
| Palu | mixed | kek | KEK | 1.0 TWh | 4.2 |
| Tanjung Lesung | mixed | kek | KEK | 1.0 TWh | 0.0 |
| Master Steel Jakarta | steel | standalone | industrial | 1.0 TWh | 11.8 |
| Semen Padang Indarung | cement | standalone | industrial | 968 GWh | 22.3 |
| Gunung Raja Paksi Bekasi | steel | standalone | industrial | 910 GWh | 54.0 |
| Semen Tonasa | cement | standalone | industrial | 814 GWh | 21.0 |
| Morotai | mixed | kek | KEK | 744 GWh | 0.0 |
| Lido | mixed | kek | KEK | 702 GWh | 1.2 |
| Mandalika | mixed | kek | KEK | 699 GWh | 2.7 |
| Kendal | mixed | kek | KEK | 675 GWh | 13.4 |
| Krakatau Posco Cilegon | steel | standalone | industrial | 600 GWh | 0.8 |
| Conch Cement Serang | cement | standalone | industrial | 484 GWh | 4.2 |
| Semen Bosowa Maros | cement | standalone | industrial | 462 GWh | 0.8 |
| Jakarta Prima Steel Industries | steel | standalone | industrial | 450 GWh | 9.1 |
| Semen Baturaja | cement | standalone | industrial | 424 GWh | 6.1 |
| SBI Tuban | cement | standalone | industrial | 410 GWh | 6.3 |
| Indocement Palimanan | cement | standalone | industrial | 398 GWh | 17.8 |
| Cemindo Gemilang Bayah | cement | standalone | industrial | 385 GWh | 10.7 |
| Maloy Batuta Trans Kalimantan | mixed | kek | KEK | 376 GWh | 0.0 |
| Bitung | mixed | kek | KEK | 360 GWh | 13.9 |
| SBI Cilacap | cement | standalone | industrial | 355 GWh | 10.2 |
| Sorong | mixed | kek | KEK | 353 GWh | 0.0 |
| Ispat Indo Sidoarjo | steel | standalone | industrial | 350 GWh | 10.0 |
| Kura Kura Bali | mixed | kek | KEK | 336 GWh | 0.0 |
| Semeru Surya Semen Kutai | cement | standalone | industrial | 330 GWh | 2.7 |
| SI Gresik Rembang | cement | standalone | industrial | 330 GWh | 11.1 |
| Semen Imasco Asiatic Jember | cement | standalone | industrial | 330 GWh | 4.6 |
| Tanjung Kelayang | mixed | kek | KEK | 219 GWh | 0.0 |
| Semen Bosowa Banyuwangi | cement | standalone | industrial | 198 GWh | 2.1 |
| Cemindo Gemilang Ciwandan | cement | standalone | industrial | 192 GWh | 2.6 |
| Likupang | mixed | kek | KEK | 133 GWh | 0.0 |
| Nongsa | mixed | kek | KEK | 112 GWh | 4.0 |
| Semen Gresik City | cement | standalone | industrial | 99 GWh | 14.2 |
| Singhasari | mixed | kek | KEK | 81 GWh | 0.0 |
| Semen Kupang | cement | standalone | industrial | 55 GWh | 7.7 |
| Banten International Education, Technology, and Health | mixed | kek | KEK | 40 GWh | 0.9 |
| Batam Tourism and International Healthcare | mixed | kek | KEK | 32 GWh | 2.6 |
| Sanur | mixed | kek | KEK | 28 GWh | 2.7 |
| Batam Aero Technic | mixed | kek | KEK | 20 GWh | 5.1 |
| Setangga | mixed | kek | KEK | — | 0.0 |
| Tanjung Sauh | mixed | kek | KEK | — | 0.0 |

## Uncovered (22 sites — sorted by demand)

| Site | Sector | Type | Polygon | Demand | Rooftop MWp |
|------|--------|------|---------|--------|-------------|
| Nusantara Industri Sejati | nickel | cluster | — | 75.0 TWh | 0.0 |
| Inalum Asahan | aluminium | standalone | — | 3.8 TWh | 0.0 |
| Pupuk Kaltim Bontang | fertilizer | standalone | — | 2.4 TWh | 47.3 |
| Pupuk Sriwidjaja Palembang | fertilizer | standalone | — | 2.0 TWh | 319.3 |
| Buli Industrial Park | nickel | cluster | — | 1.5 TWh | 0.0 |
| Dexin Steel Morowali | steel | standalone | — | 1.4 TWh | 0.6 |
| SBI Narogong | cement | standalone | — | 667 GWh | 8.5 |
| Conch Cement North Sulawesi | cement | standalone | — | 484 GWh | 6.9 |
| Red Lion Hongshi Tonga | cement | standalone | — | 440 GWh | 0.5 |
| Indocement Kotabaru Tarjun | cement | standalone | — | 286 GWh | 21.9 |
| Semen Garuda Bekasi | cement | standalone | — | 275 GWh | 22.2 |
| Semen Grobogan | cement | standalone | — | 275 GWh | 10.7 |
| SBI Andalas Lhoknga | cement | standalone | — | 202 GWh | 5.1 |
| Semen Jawa SCG Sukabumi | cement | standalone | — | 198 GWh | 33.7 |
| Conch South Kalimantan | cement | standalone | — | 165 GWh | 0.0 |
| Cemindo Gemilang Batam | cement | standalone | — | 132 GWh | 39.6 |
| Semen Bosowa Batam | cement | standalone | — | 132 GWh | 11.4 |
| Semen Jakarta | cement | standalone | — | 110 GWh | 15.2 |
| Solusi Bangun Cilegon | cement | standalone | — | 66 GWh | 25.2 |
| Conch West Kalimantan | cement | standalone | — | 55 GWh | 19.4 |
| Stardust Estate Invesment (SEI) | nickel | cluster | — | — | 0.0 |
| Indonesia Konawe Industrial Park (IKIP) | nickel | cluster | — | — | 0.0 |
