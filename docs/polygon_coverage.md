# Polygon coverage by site

Auto-generated. Regenerate via:

```bash
PYTHONPATH=. uv run python scripts/audit_polygon_coverage.py
PYTHONPATH=. uv run python scripts/generate_polygon_coverage_md.py
```

**Source:** `outputs/data/processed/polygon_coverage_priority.csv`


## Summary

- **Sites covered:** 42 / 81 (52%)
  - KEK polygons: 25 / 25
  - Industrial polygons: 17 / 56
- **Demand covered:** 560.2 TWh / 662.4 TWh (**84.6%**)
- **Demand uncovered:** 102.2 TWh (15.4%)

Demand is `capacity_annual_tonnes × SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` for industrial sites and `area_ha × intensity_per_ha` for KEKs (same formula `fct_site_demand` uses). NaN-demand rows excluded from totals.

## Marginal lever — top uncovered sites by cumulative demand share

Add a polygon to these in order, biggest impact first.

| # | Site | Sector | Demand | Cumulative % of total |
|---|------|--------|--------|-----------------------|
| 1 | Nusantara Industri Sejati | nickel | 75.0 TWh | 11.3% |
| 2 | Inalum Asahan | aluminium | 3.8 TWh | 11.9% |
| 3 | Pupuk Kaltim Bontang | fertilizer | 2.4 TWh | 12.3% |
| 4 | Krakatau Steel Cilegon | steel | 2.0 TWh | 12.6% |
| 5 | Pupuk Sriwidjaja Palembang | fertilizer | 2.0 TWh | 12.9% |
| 6 | Semen Gresik Tuban | cement | 1.6 TWh | 13.1% |
| 7 | Buli Industrial Park | nickel | 1.5 TWh | 13.3% |
| 8 | Dexin Steel Morowali | steel | 1.4 TWh | 13.5% |
| 9 | Indocement Citeureup | cement | 1.3 TWh | 13.7% |
| 10 | Pupuk Kujang Cikampek | fertilizer | 1.1 TWh | 13.9% |
| 11 | Pupuk Iskandar Muda Lhokseumawe | fertilizer | 1.1 TWh | 14.1% |
| 12 | Master Steel Jakarta | steel | 1.0 TWh | 14.2% |
| 13 | Semen Tonasa | cement | 814 GWh | 14.4% |
| 14 | SBI Narogong | cement | 667 GWh | 14.5% |
| 15 | Conch Cement Serang | cement | 484 GWh | 14.5% |

After the top 5, marginal lift drops below 1 percentage point per site.

## Covered (42 sites)

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
| Industropolis Batang | mixed | kek | KEK | 1.9 TWh | 2.7 |
| Arun Lhokseumawe | mixed | kek | KEK | 1.8 TWh | 42.4 |
| Galang Batang | mixed | kek | KEK | 1.6 TWh | 6.7 |
| Gresik | mixed | kek | KEK | 1.5 TWh | 16.0 |
| Sei Mangkei | mixed | kek | KEK | 1.4 TWh | 6.5 |
| Palu | mixed | kek | KEK | 1.0 TWh | 4.2 |
| Tanjung Lesung | mixed | kek | KEK | 1.0 TWh | 0.0 |
| Semen Padang Indarung | cement | standalone | industrial | 968 GWh | 22.3 |
| Gunung Raja Paksi Bekasi | steel | standalone | industrial | 910 GWh | 54.0 |
| Morotai | mixed | kek | KEK | 744 GWh | 0.0 |
| Lido | mixed | kek | KEK | 702 GWh | 1.2 |
| Mandalika | mixed | kek | KEK | 699 GWh | 2.7 |
| Kendal | mixed | kek | KEK | 675 GWh | 13.4 |
| Krakatau Posco Cilegon | steel | standalone | industrial | 600 GWh | 0.8 |
| Semen Baturaja | cement | standalone | industrial | 424 GWh | 6.1 |
| Indocement Palimanan | cement | standalone | industrial | 398 GWh | 17.8 |
| Cemindo Gemilang Bayah | cement | standalone | industrial | 385 GWh | 10.7 |
| Maloy Batuta Trans Kalimantan | mixed | kek | KEK | 376 GWh | 0.0 |
| Bitung | mixed | kek | KEK | 360 GWh | 13.9 |
| Sorong | mixed | kek | KEK | 353 GWh | 0.0 |
| Ispat Indo Sidoarjo | steel | standalone | industrial | 350 GWh | 10.0 |
| Kura Kura Bali | mixed | kek | KEK | 336 GWh | 0.0 |
| Tanjung Kelayang | mixed | kek | KEK | 219 GWh | 0.0 |
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

## Uncovered (39 sites — sorted by demand)

| Site | Sector | Type | Polygon | Demand | Rooftop MWp |
|------|--------|------|---------|--------|-------------|
| Nusantara Industri Sejati | nickel | cluster | — | 75.0 TWh | 0.0 |
| Inalum Asahan | aluminium | standalone | — | 3.8 TWh | 0.0 |
| Pupuk Kaltim Bontang | fertilizer | standalone | — | 2.4 TWh | 47.3 |
| Krakatau Steel Cilegon | steel | standalone | — | 2.0 TWh | 150.8 |
| Pupuk Sriwidjaja Palembang | fertilizer | standalone | — | 2.0 TWh | 319.3 |
| Semen Gresik Tuban | cement | standalone | — | 1.6 TWh | 42.0 |
| Buli Industrial Park | nickel | cluster | — | 1.5 TWh | 0.0 |
| Dexin Steel Morowali | steel | standalone | — | 1.4 TWh | 0.6 |
| Indocement Citeureup | cement | standalone | — | 1.3 TWh | 169.8 |
| Pupuk Kujang Cikampek | fertilizer | standalone | — | 1.1 TWh | 163.0 |
| Pupuk Iskandar Muda Lhokseumawe | fertilizer | standalone | — | 1.1 TWh | 11.3 |
| Master Steel Jakarta | steel | standalone | — | 1.0 TWh | 337.7 |
| Semen Tonasa | cement | standalone | — | 814 GWh | 45.1 |
| SBI Narogong | cement | standalone | — | 667 GWh | 8.5 |
| Conch Cement Serang | cement | standalone | — | 484 GWh | 25.8 |
| Conch Cement North Sulawesi | cement | standalone | — | 484 GWh | 6.9 |
| Semen Bosowa Maros | cement | standalone | — | 462 GWh | 5.8 |
| Jakarta Prima Steel Industries | steel | standalone | — | 450 GWh | 251.0 |
| Red Lion Hongshi Tonga | cement | standalone | — | 440 GWh | 0.5 |
| SBI Tuban | cement | standalone | — | 410 GWh | 15.5 |
| SBI Cilacap | cement | standalone | — | 355 GWh | 139.4 |
| Semeru Surya Semen Kutai | cement | standalone | — | 330 GWh | 29.2 |
| SI Gresik Rembang | cement | standalone | — | 330 GWh | 15.6 |
| Semen Imasco Asiatic Jember | cement | standalone | — | 330 GWh | 33.5 |
| Indocement Kotabaru Tarjun | cement | standalone | — | 286 GWh | 21.9 |
| Semen Garuda Bekasi | cement | standalone | — | 275 GWh | 22.2 |
| Semen Grobogan | cement | standalone | — | 275 GWh | 10.7 |
| SBI Andalas Lhoknga | cement | standalone | — | 202 GWh | 5.1 |
| Semen Jawa SCG Sukabumi | cement | standalone | — | 198 GWh | 33.7 |
| Semen Bosowa Banyuwangi | cement | standalone | — | 198 GWh | 53.2 |
| Cemindo Gemilang Ciwandan | cement | standalone | — | 192 GWh | 55.8 |
| Conch South Kalimantan | cement | standalone | — | 165 GWh | 0.0 |
| Cemindo Gemilang Batam | cement | standalone | — | 132 GWh | 39.6 |
| Semen Bosowa Batam | cement | standalone | — | 132 GWh | 11.4 |
| Semen Jakarta | cement | standalone | — | 110 GWh | 15.2 |
| Solusi Bangun Cilegon | cement | standalone | — | 66 GWh | 25.2 |
| Conch West Kalimantan | cement | standalone | — | 55 GWh | 19.4 |
| Stardust Estate Invesment (SEI) | nickel | cluster | — | — | 0.0 |
| Indonesia Konawe Industrial Park (IKIP) | nickel | cluster | — | — | 0.0 |
