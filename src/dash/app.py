"""KEK Power Competitiveness Dashboard — Plotly Dash application.

Usage:
    uv run python -m src.dash.app

Entry point: create_app() returns a configured Dash instance.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from src.dash.constants import (
    ACTION_FLAG_COLORS,
    ACTION_FLAG_DESCRIPTIONS,
    ACTION_FLAG_LABELS,
    MAP_CENTER,
    MAP_ZOOM,
    TABLE_COLUMNS,
    TIER1_SLIDERS,
    TIER2_SLIDERS,
    TIER3_SLIDERS,
    WACC_DEFAULT,
    WACC_DESCRIPTION,
    WACC_MARKS,
    WACC_MAX,
    WACC_MIN,
    WACC_STEP,
)
from src.dash.data_loader import (
    DataLoadError,
    compute_ruptl_region_metrics,
    load_all_data,
    prepare_resource_df,
)
from src.dash.logic import (
    UserAssumptions,
    UserThresholds,
    compute_scorecard_live,
    get_default_assumptions,
    get_default_thresholds,
)
from src.dash.map_layers import LAYER_OPTIONS, get_all_layers

# ---------------------------------------------------------------------------
# Module-level data (loaded once at startup, never changes)
# ---------------------------------------------------------------------------

_DATA: dict | None = None
_RESOURCE_DF = None
_RUPTL_METRICS = None
_DEMAND_DF = None
_GRID_DF = None


def _load_data():
    """Load and cache all pipeline data at module level."""
    global _DATA, _RESOURCE_DF, _RUPTL_METRICS, _DEMAND_DF, _GRID_DF
    if _DATA is not None:
        return

    _DATA = load_all_data()
    _RESOURCE_DF = prepare_resource_df(_DATA)
    _RUPTL_METRICS = compute_ruptl_region_metrics(_DATA["fct_ruptl_pipeline"])
    _DEMAND_DF = _DATA["fct_kek_demand"]
    _GRID_DF = _DATA["fct_grid_cost_proxy"]

    # Pre-load map layers (rasters are downsampled and cached as base64 PNGs)
    get_all_layers()


# ---------------------------------------------------------------------------
# Layout builders
# ---------------------------------------------------------------------------


def _build_sidebar():
    """Assumptions panel with 3 collapsible tiers."""
    defaults = get_default_assumptions()
    default_thresholds = get_default_thresholds()

    def _slider(slider_id, config, default_val):
        label_id = f"label-{slider_id}"
        label_text = f"{config['label']} ({config['unit']})" if config["unit"] else config["label"]
        children = [
            html.Label(
                [label_text, html.Span(" ?", className="text-muted", style={"fontSize": "11px"})],
                id=label_id,
                className="mb-1 small fw-bold",
                style={"cursor": "help"},
            ),
            dbc.Tooltip(config.get("description", ""), target=label_id, placement="top"),
            dcc.Slider(
                id=slider_id,
                min=config["min"],
                max=config["max"],
                step=config["step"],
                value=default_val,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ]
        return html.Div(children, className="mb-3")

    # Tier 1: Primary controls
    tier1 = html.Div(
        [
            html.H6("Core Assumptions", className="text-primary mb-3"),
            html.Div(
                [
                    html.Label(
                        [
                            "WACC (%)",
                            html.Span(" ?", className="text-muted", style={"fontSize": "11px"}),
                        ],
                        id="label-slider-wacc",
                        className="mb-1 small fw-bold",
                        style={"cursor": "help"},
                    ),
                    dbc.Tooltip(WACC_DESCRIPTION, target="label-slider-wacc", placement="top"),
                    dcc.Slider(
                        id="slider-wacc",
                        min=WACC_MIN,
                        max=WACC_MAX,
                        step=WACC_STEP,
                        value=WACC_DEFAULT,
                        marks=WACC_MARKS,
                    ),
                ],
                className="mb-3",
            ),
            _slider("slider-capex", TIER1_SLIDERS["capex_usd_per_kw"], defaults.capex_usd_per_kw),
            _slider("slider-lifetime", TIER1_SLIDERS["lifetime_yr"], defaults.lifetime_yr),
        ]
    )

    # Tier 2: Infrastructure costs
    tier2_sliders = []
    for key, config in TIER2_SLIDERS.items():
        default_val = getattr(defaults, key)
        tier2_sliders.append(_slider(f"slider-{key}", config, default_val))

    tier2 = html.Div(
        [
            dbc.Button(
                "Advanced Assumptions",
                id="collapse-tier2-btn",
                color="link",
                size="sm",
                className="p-0 mb-2",
            ),
            dbc.Collapse(
                html.Div(tier2_sliders),
                id="collapse-tier2",
                is_open=False,
            ),
        ]
    )

    # Tier 3: Flag thresholds
    tier3_sliders = []
    for key, config in TIER3_SLIDERS.items():
        default_val = getattr(default_thresholds, key)
        tier3_sliders.append(_slider(f"slider-{key}", config, default_val))

    tier3 = html.Div(
        [
            dbc.Button(
                "Flag Thresholds",
                id="collapse-tier3-btn",
                color="link",
                size="sm",
                className="p-0 mb-2",
            ),
            dbc.Collapse(
                html.Div(tier3_sliders),
                id="collapse-tier3",
                is_open=False,
            ),
        ]
    )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H5("Assumptions", className="card-title"),
                    tier1,
                    html.Hr(),
                    html.Div(
                        [
                            html.Label("Grid Cost Benchmark", className="mb-1 small fw-bold"),
                            dbc.RadioItems(
                                id="radio-grid-benchmark",
                                options=[
                                    {"label": "I-4/TT Tariff (uniform $63/MWh)", "value": "tariff"},
                                    {"label": "Regional BPP (generation cost)", "value": "bpp"},
                                ],
                                value="tariff",
                                inline=False,
                                className="small",
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Hr(),
                    tier2,
                    html.Hr(),
                    tier3,
                    html.Hr(),
                    dbc.Button("Reset to Defaults", id="btn-reset", color="secondary", size="sm"),
                ]
            )
        ],
        className="mb-3",
    )


def _flag_legend_popover(target_id):
    """Build a popover explaining all action flag colors."""
    items = []
    for flag, color in ACTION_FLAG_COLORS.items():
        items.append(
            html.Div(
                [
                    html.Span(
                        "\u25cf ",
                        style={"color": color, "fontSize": "16px", "marginRight": "4px"},
                    ),
                    html.Span(ACTION_FLAG_LABELS[flag], className="fw-bold small"),
                    html.Span(
                        f" \u2014 {ACTION_FLAG_DESCRIPTIONS[flag]}",
                        className="small text-muted",
                    ),
                ],
                className="mb-1",
            )
        )
    return dbc.Popover(
        dbc.PopoverBody(items),
        target=target_id,
        trigger="hover",
        placement="bottom",
    )


def _build_map():
    """Overview map with KEK markers and toggleable layers."""
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    "KEK Overview Map ",
                    dbc.Badge(
                        "?",
                        id="info-map-legend",
                        color="secondary",
                        pill=True,
                        style={"cursor": "help"},
                    ),
                    _flag_legend_popover("info-map-legend"),
                ]
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dcc.Graph(id="map-graph", style={"height": "600px"}),
                                width=10,
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        html.Label(
                                            [
                                                "Map Layers ",
                                                dbc.Badge(
                                                    "?",
                                                    id="info-map-layers",
                                                    color="secondary",
                                                    pill=True,
                                                    style={
                                                        "cursor": "help",
                                                        "fontSize": "9px",
                                                    },
                                                ),
                                            ],
                                            className="fw-bold small mb-2",
                                        ),
                                        dbc.Popover(
                                            dbc.PopoverBody(
                                                [
                                                    html.P(
                                                        "Solar Buildable Area shows land where solar PV "
                                                        "can actually be built, after removing:",
                                                        className="small mb-1",
                                                    ),
                                                    html.Ul(
                                                        [
                                                            html.Li(
                                                                "Protected forest (Kawasan Hutan)",
                                                                className="small",
                                                            ),
                                                            html.Li(
                                                                "Peatland (KLHK)",
                                                                className="small",
                                                            ),
                                                            html.Li(
                                                                "Cropland, water, urban, mangroves (ESA WorldCover)",
                                                                className="small",
                                                            ),
                                                            html.Li(
                                                                "Steep slopes (>8 deg) and high elevation (>1500m)",
                                                                className="small",
                                                            ),
                                                        ],
                                                        className="small mb-1 ps-3",
                                                    ),
                                                    html.P(
                                                        "Only 15% of Indonesia's land passes all filters.",
                                                        className="small text-muted mb-0",
                                                    ),
                                                ]
                                            ),
                                            target="info-map-layers",
                                            trigger="hover",
                                            placement="left",
                                        ),
                                        dbc.Checklist(
                                            id="map-layer-toggle",
                                            options=LAYER_OPTIONS,
                                            value=[],
                                            className="small",
                                        ),
                                    ],
                                    className="pt-2",
                                ),
                                width=2,
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


def _build_table():
    """Ranked table of all KEKs."""
    return dbc.Card(
        [
            dbc.CardHeader("Ranked Table"),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Label("Filter by action flag:", className="me-2"),
                            dcc.Dropdown(
                                id="filter-action-flag",
                                options=[
                                    {"label": v, "value": k} for k, v in ACTION_FLAG_LABELS.items()
                                ],
                                multi=True,
                                placeholder="All flags",
                                className="mb-2",
                            ),
                        ]
                    ),
                    dash.dash_table.DataTable(
                        id="ranked-table",
                        columns=[{"name": v, "id": k} for k, v in TABLE_COLUMNS.items()],
                        sort_action="native",
                        filter_action="native",
                        page_size=25,
                        export_format="csv",
                        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                        style_data_conditional=[
                            {
                                "if": {"filter_query": f'{{action_flag}} = "{flag}"'},
                                "backgroundColor": f"{color}15",
                            }
                            for flag, color in ACTION_FLAG_COLORS.items()
                        ],
                    ),
                ]
            ),
        ]
    )


def _build_quadrant():
    """Quadrant chart: LCOE vs grid cost."""
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    "Quadrant Chart: Solar LCOE vs Grid Cost ",
                    dbc.Badge(
                        "?",
                        id="info-quadrant-legend",
                        color="secondary",
                        pill=True,
                        style={"cursor": "help"},
                    ),
                    _flag_legend_popover("info-quadrant-legend"),
                ]
            ),
            dbc.CardBody(dcc.Graph(id="quadrant-graph", style={"height": "500px"})),
        ]
    )


def _build_scorecard():
    """KEK detail scorecard panel."""
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.Span("KEK Scorecard — ", className="fw-bold"),
                    html.Span(id="scorecard-kek-name", children="Select a KEK"),
                ]
            ),
            dbc.CardBody(
                id="scorecard-body",
                children=html.P(
                    "Click a KEK on the map or table to view details.",
                    className="text-muted",
                ),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> dash.Dash:
    """Create and configure the Dash application."""
    try:
        _load_data()
    except DataLoadError as e:
        # Return a minimal error app
        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
        app.layout = dbc.Container(
            [
                dbc.Alert(
                    [html.H4("Data not found"), html.P(str(e))],
                    color="danger",
                    className="mt-4",
                )
            ]
        )
        return app

    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        suppress_callback_exceptions=True,
    )

    # --- Layout ---
    app.layout = dbc.Container(
        [
            # Stores
            dcc.Store(id="user-assumptions", data=get_default_assumptions().to_dict()),
            dcc.Store(id="user-thresholds", data=get_default_thresholds().to_dict()),
            dcc.Store(id="selected-kek", data=None),
            dcc.Store(id="scorecard-live-data", data=None),
            # Header
            dbc.Navbar(
                dbc.Container(
                    [
                        dbc.NavbarBrand("Indonesia KEK Power Competitiveness", className="fw-bold"),
                        html.Span(
                            "25 KEKs | Solar + Wind | Live LCOE", className="text-light small"
                        ),
                    ]
                ),
                color="dark",
                dark=True,
                className="mb-3",
            ),
            # Main layout: sidebar + content
            dbc.Row(
                [
                    # Sidebar
                    dbc.Col(_build_sidebar(), width=3),
                    # Main content
                    dbc.Col(
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(
                                        label="Map",
                                        tab_id="tab-map",
                                        children=html.Div(_build_map(), className="mt-3"),
                                    ),
                                    dbc.Tab(
                                        label="Table",
                                        tab_id="tab-table",
                                        children=html.Div(_build_table(), className="mt-3"),
                                    ),
                                    dbc.Tab(
                                        label="Quadrant",
                                        tab_id="tab-quadrant",
                                        children=html.Div(_build_quadrant(), className="mt-3"),
                                    ),
                                ],
                                id="main-tabs",
                                active_tab="tab-map",
                            ),
                            html.Div(_build_scorecard(), className="mt-3"),
                        ],
                        width=9,
                    ),
                ]
            ),
        ],
        fluid=True,
    )

    # --- Register callbacks ---
    _register_callbacks(app)

    return app


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


def _register_callbacks(app: dash.Dash):
    """Register all dashboard callbacks."""

    # Collapse toggles
    @app.callback(
        Output("collapse-tier2", "is_open"),
        Input("collapse-tier2-btn", "n_clicks"),
        State("collapse-tier2", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_tier2(n, is_open):
        return not is_open

    @app.callback(
        Output("collapse-tier3", "is_open"),
        Input("collapse-tier3-btn", "n_clicks"),
        State("collapse-tier3", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_tier3(n, is_open):
        return not is_open

    # Assumptions store update
    @app.callback(
        Output("user-assumptions", "data"),
        [
            Input("slider-wacc", "value"),
            Input("slider-capex", "value"),
            Input("slider-lifetime", "value"),
        ]
        + [Input(f"slider-{k}", "value") for k in TIER2_SLIDERS],
        prevent_initial_call=True,
    )
    def update_assumptions(wacc, capex, lifetime, *tier2_values):
        tier2_keys = list(TIER2_SLIDERS.keys())
        kwargs = {
            "wacc_pct": float(wacc),
            "capex_usd_per_kw": float(capex),
            "lifetime_yr": int(lifetime),
        }
        for key, val in zip(tier2_keys, tier2_values):
            kwargs[key] = float(val)
        return UserAssumptions(**kwargs).to_dict()

    # Thresholds store update
    @app.callback(
        Output("user-thresholds", "data"),
        [Input(f"slider-{k}", "value") for k in TIER3_SLIDERS],
        prevent_initial_call=True,
    )
    def update_thresholds(*values):
        keys = list(TIER3_SLIDERS.keys())
        kwargs = {k: float(v) for k, v in zip(keys, values)}
        return UserThresholds(**kwargs).to_dict()

    # Reset to defaults
    @app.callback(
        [
            Output("slider-wacc", "value"),
            Output("slider-capex", "value"),
            Output("slider-lifetime", "value"),
        ]
        + [Output(f"slider-{k}", "value") for k in TIER2_SLIDERS]
        + [Output(f"slider-{k}", "value") for k in TIER3_SLIDERS],
        Input("btn-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_defaults(n):
        d = get_default_assumptions()
        t = get_default_thresholds()
        return (
            [
                d.wacc_pct,
                d.capex_usd_per_kw,
                d.lifetime_yr,
            ]
            + [getattr(d, k) for k in TIER2_SLIDERS]
            + [getattr(t, k) for k in TIER3_SLIDERS]
        )

    # Live recomputation: assumptions/thresholds -> scorecard-live-data store
    @app.callback(
        Output("scorecard-live-data", "data"),
        [
            Input("user-assumptions", "data"),
            Input("user-thresholds", "data"),
            Input("radio-grid-benchmark", "value"),
        ],
    )
    def recompute_scorecard(assumptions_data, thresholds_data, benchmark_mode):
        assumptions = UserAssumptions.from_dict(assumptions_data)
        thresholds = UserThresholds.from_dict(thresholds_data)

        # Build per-region BPP dict when BPP mode selected
        grid_cost_by_region = None
        if benchmark_mode == "bpp":
            grid_proxy = _DATA["fct_grid_cost_proxy"]
            grid_cost_by_region = dict(zip(grid_proxy["grid_region_id"], grid_proxy["bpp_usd_mwh"]))

        result = compute_scorecard_live(
            _RESOURCE_DF,
            assumptions,
            thresholds,
            _RUPTL_METRICS,
            _DEMAND_DF,
            _GRID_DF,
            grid_cost_by_region=grid_cost_by_region,
        )
        return result.to_dict("records")

    # Map
    @app.callback(
        Output("map-graph", "figure"),
        [Input("scorecard-live-data", "data"), Input("map-layer-toggle", "value")],
    )
    def update_map(scorecard_data, active_layers):
        import plotly.graph_objects as go

        if not scorecard_data:
            scorecard = _DATA["fct_kek_scorecard"]
        else:
            scorecard = _pd_from_records(scorecard_data)
            dim = _DATA["dim_kek"][["kek_id", "kek_name", "latitude", "longitude"]]
            for col in dim.columns:
                if col != "kek_id" and col not in scorecard.columns:
                    scorecard = scorecard.merge(dim[["kek_id", col]], on="kek_id", how="left")

        active_layers = active_layers or []
        layers = get_all_layers()

        fig = go.Figure()

        # Raster image overlays via mapbox layers
        mapbox_layers = []
        for layer_key in ["pvout", "buildable", "wind"]:
            if layer_key in active_layers and layers.get(layer_key):
                b64_png, coordinates = layers[layer_key]
                mapbox_layers.append(
                    {
                        "sourcetype": "image",
                        "source": b64_png,
                        "coordinates": coordinates,
                        "below": "traces",
                        "opacity": 0.7,
                    }
                )

        # Substation points
        if "substations" in active_layers and layers.get("substations"):
            subs = layers["substations"]
            fig.add_trace(
                go.Scattermapbox(
                    lat=[s["lat"] for s in subs],
                    lon=[s["lon"] for s in subs],
                    mode="markers",
                    marker=dict(size=4, color="#666666", opacity=0.6),
                    text=[f"{s['name']}<br>{s['voltage']} | {s['capacity_mva']} MVA" for s in subs],
                    hovertemplate="%{text}<extra>Substation</extra>",
                    name="Substations",
                )
            )

        # KEK boundary polygons
        if "kek_polygons" in active_layers and layers.get("kek_polygons"):
            gj = layers["kek_polygons"]
            # Extract polygon outlines as Scattermapbox lines
            for feat in gj.get("features", []):
                geom = feat.get("geometry", {})
                props = feat.get("properties", {})
                name = props.get("title", props.get("slug", ""))
                coords_list = geom.get("coordinates", [])
                if geom.get("type") == "MultiPolygon":
                    for poly in coords_list:
                        ring = poly[0]
                        lats = [c[1] for c in ring]
                        lons = [c[0] for c in ring]
                        fig.add_trace(
                            go.Scattermapbox(
                                lat=lats,
                                lon=lons,
                                mode="lines",
                                line=dict(width=2, color="#E91E63"),
                                hoverinfo="text",
                                text=name,
                                showlegend=False,
                            )
                        )
                elif geom.get("type") == "Polygon":
                    ring = coords_list[0]
                    lats = [c[1] for c in ring]
                    lons = [c[0] for c in ring]
                    fig.add_trace(
                        go.Scattermapbox(
                            lat=lats,
                            lon=lons,
                            mode="lines",
                            line=dict(width=2, color="#E91E63"),
                            hoverinfo="text",
                            text=name,
                            showlegend=False,
                        )
                    )
            # Add a single invisible trace for the legend entry
            fig.add_trace(
                go.Scattermapbox(
                    lat=[None],
                    lon=[None],
                    mode="lines",
                    line=dict(width=2, color="#E91E63"),
                    name="KEK Boundaries",
                )
            )

        # KEK action flag markers (always on top)
        if "action_flag" in scorecard.columns:
            for flag, color in ACTION_FLAG_COLORS.items():
                subset = scorecard[scorecard["action_flag"] == flag]
                fig.add_trace(
                    go.Scattermapbox(
                        lat=subset["latitude"] if not subset.empty else [],
                        lon=subset["longitude"] if not subset.empty else [],
                        mode="markers",
                        marker=dict(size=12, color=color),
                        text=subset["kek_name"]
                        if not subset.empty and "kek_name" in subset.columns
                        else (subset["kek_id"] if not subset.empty else []),
                        customdata=subset["kek_id"] if not subset.empty else [],
                        hovertemplate="<b>%{text}</b><extra></extra>",
                        name=ACTION_FLAG_LABELS.get(flag, flag),
                    )
                )
        else:
            fig.add_trace(
                go.Scattermapbox(
                    lat=scorecard["latitude"],
                    lon=scorecard["longitude"],
                    mode="markers",
                    marker=dict(size=12, color="#1565C0"),
                    text=scorecard["kek_name"]
                    if "kek_name" in scorecard.columns
                    else scorecard["kek_id"],
                    customdata=scorecard["kek_id"],
                    hovertemplate="<b>%{text}</b><extra></extra>",
                    name="KEKs",
                )
            )

        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=MAP_CENTER,
                zoom=MAP_ZOOM,
                layers=mapbox_layers,
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        )
        return fig

    # Ranked table
    @app.callback(
        Output("ranked-table", "data"),
        [Input("scorecard-live-data", "data"), Input("filter-action-flag", "value")],
    )
    def update_table(scorecard_data, flag_filter):
        if not scorecard_data:
            df = _DATA["fct_kek_scorecard"]
        else:
            df = _pd_from_records(scorecard_data)
            # Merge display columns from precomputed scorecard
            precomputed = _DATA["fct_kek_scorecard"]
            merge_cols = [
                c for c in TABLE_COLUMNS if c not in df.columns and c in precomputed.columns
            ]
            if merge_cols:
                df = df.merge(precomputed[["kek_id"] + merge_cols], on="kek_id", how="left")

        if flag_filter and "action_flag" in df.columns:
            df = df[df["action_flag"].isin(flag_filter)]

        display_cols = [c for c in TABLE_COLUMNS if c in df.columns]
        return df[display_cols].round(2).to_dict("records")

    # Quadrant chart
    @app.callback(
        Output("quadrant-graph", "figure"),
        [Input("scorecard-live-data", "data"), Input("radio-grid-benchmark", "value")],
    )
    def update_quadrant(scorecard_data, benchmark_mode):
        import plotly.graph_objects as go

        if not scorecard_data:
            sc = _DATA["fct_kek_scorecard"]
        else:
            sc = _pd_from_records(scorecard_data)
            precomputed = _DATA["fct_kek_scorecard"]
            for col in ["kek_name", "grid_region_id"]:
                if col not in sc.columns and col in precomputed.columns:
                    sc = sc.merge(precomputed[["kek_id", col]], on="kek_id", how="left")

        # Join grid cost data
        grid_proxy = _DATA["fct_grid_cost_proxy"][
            ["grid_region_id", "bpp_usd_mwh", "dashboard_rate_usd_mwh"]
        ]
        if "grid_region_id" not in sc.columns:
            dim = _DATA["dim_kek"][["kek_id", "grid_region_id"]]
            sc = sc.merge(dim, on="kek_id", how="left")
        sc = sc.merge(grid_proxy, on="grid_region_id", how="left")

        # Y-axis: BPP or uniform tariff based on radio button
        if benchmark_mode == "bpp":
            sc["grid_cost_y"] = sc["bpp_usd_mwh"].fillna(sc["dashboard_rate_usd_mwh"])
            y_label = "PLN Generation Cost — BPP ($/MWh)"
        else:
            sc["grid_cost_y"] = sc["dashboard_rate_usd_mwh"]
            y_label = "I-4/TT Industrial Tariff ($/MWh)"

        fig = go.Figure()

        if "action_flag" in sc.columns:
            for flag, color in ACTION_FLAG_COLORS.items():
                subset = sc[sc["action_flag"] == flag]
                fig.add_trace(
                    go.Scatter(
                        x=subset["lcoe_mid_usd_mwh"] if not subset.empty else [],
                        y=subset["grid_cost_y"] if not subset.empty else [],
                        mode="markers+text",
                        marker=dict(size=14, color=color),
                        text=subset.get("kek_name", subset["kek_id"]) if not subset.empty else [],
                        textposition="top center",
                        textfont=dict(size=9),
                        name=ACTION_FLAG_LABELS.get(flag, flag),
                        hovertemplate="<b>%{text}</b><br>LCOE: $%{x:.1f}/MWh<br>Grid: $%{y:.1f}/MWh<extra></extra>",
                    )
                )

        # Parity line
        max_val = (
            max(
                sc["lcoe_mid_usd_mwh"].max() if sc["lcoe_mid_usd_mwh"].notna().any() else 100,
                sc["grid_cost_y"].max() if sc["grid_cost_y"].notna().any() else 100,
            )
            + 20
        )
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(dash="dash", color="gray"),
                showlegend=False,
                name="Parity",
            )
        )

        fig.update_layout(
            xaxis_title="Solar LCOE ($/MWh)",
            yaxis_title=y_label,
            margin=dict(l=50, r=20, t=30, b=50),
        )
        return fig

    # Map click -> selected KEK
    @app.callback(
        Output("selected-kek", "data"),
        Input("map-graph", "clickData"),
        prevent_initial_call=True,
    )
    def map_click(click_data):
        if click_data and click_data.get("points"):
            point = click_data["points"][0]
            return point.get("customdata")
        return None

    # Table click -> selected KEK
    @app.callback(
        Output("selected-kek", "data", allow_duplicate=True),
        Input("ranked-table", "active_cell"),
        State("ranked-table", "data"),
        prevent_initial_call=True,
    )
    def table_click(active_cell, table_data):
        if active_cell and table_data:
            row = table_data[active_cell["row"]]
            return row.get("kek_id") if "kek_id" in row else row.get("kek_name")
        return None

    # Scorecard panel update
    @app.callback(
        [Output("scorecard-body", "children"), Output("scorecard-kek-name", "children")],
        [Input("selected-kek", "data"), Input("scorecard-live-data", "data")],
    )
    def update_scorecard(selected_kek, scorecard_data):
        if not selected_kek:
            return html.P(
                "Click a KEK on the map or table to view details.", className="text-muted"
            ), "Select a KEK"

        # Get scorecard data, merge resource columns for display
        if scorecard_data:
            sc = _pd_from_records(scorecard_data)
        else:
            sc = _DATA["fct_kek_scorecard"]

        # Merge resource data (pvout, buildable area, etc.)
        resource_cols = [
            "kek_id",
            "pvout_centroid",
            "pvout_best_50km",
            "buildable_area_ha",
            "max_captive_capacity_mwp",
        ]
        available = [c for c in resource_cols if c in _RESOURCE_DF.columns]
        for col in available:
            if col != "kek_id" and col not in sc.columns:
                sc = sc.merge(_RESOURCE_DF[["kek_id", col]], on="kek_id", how="left")

        kek_row = sc[sc["kek_id"] == selected_kek]
        if kek_row.empty:
            return html.P(
                f"KEK '{selected_kek}' not found.", className="text-warning"
            ), selected_kek

        kek = kek_row.iloc[0]
        kek_name = (
            _DATA["dim_kek"].set_index("kek_id").loc[selected_kek, "kek_name"]
            if selected_kek in _DATA["dim_kek"]["kek_id"].values
            else selected_kek
        )

        # Build scorecard tabs
        def _val(col, fmt=".2f"):
            v = kek.get(col)
            if v is None or (isinstance(v, float) and import_isnan(v)):
                return "---"
            return f"{v:{fmt}}"

        resource_tab = dbc.Tab(
            label="Resource",
            children=html.Div(
                [
                    _row("PVOUT centroid", _val("pvout_centroid", ".0f"), "kWh/kWp"),
                    _row("PVOUT best 50km", _val("pvout_best_50km", ".0f"), "kWh/kWp"),
                    _row("Buildable area", _val("buildable_area_ha", ".0f"), "ha"),
                    _row("Max captive capacity", _val("max_captive_capacity_mwp", ".0f"), "MWp"),
                    _row("Project viable", str(kek.get("project_viable", "---")), ""),
                ],
                className="mt-2",
            ),
        )

        lcoe_tab = dbc.Tab(
            label="LCOE",
            children=html.Div(
                [
                    _row(
                        "LCOE (low/mid/high)",
                        f"${_val('lcoe_low_usd_mwh')} / ${_val('lcoe_mid_usd_mwh')} / ${_val('lcoe_high_usd_mwh')}",
                        "/MWh",
                    ),
                    _row("Competitive gap", _val("solar_competitive_gap_pct", ".1f"), "%"),
                    _row("Solar Now", str(kek.get("solar_now", "---")), ""),
                    _row("Invest Resilience", str(kek.get("invest_resilience", "---")), ""),
                    _row("Carbon breakeven", _val("carbon_breakeven_usd_tco2", ".1f"), "$/tCO2"),
                ],
                className="mt-2",
            ),
        )

        flags_tab = dbc.Tab(
            label="Flags",
            children=html.Div(
                [
                    _row("Grid First", str(kek.get("grid_first", "---")), ""),
                    _row("Firming Needed", str(kek.get("firming_needed", "---")), ""),
                    _row("Plan Late", str(kek.get("plan_late", "---")), ""),
                    _row("Action Flag", str(kek.get("action_flag", "---")), ""),
                ],
                className="mt-2",
            ),
        )

        body = dbc.Tabs(
            [resource_tab, lcoe_tab, flags_tab],
            active_tab="tab-0",
        )
        return body, kek_name


def _row(label, value, unit):
    """Build a single scorecard data row."""
    return dbc.Row(
        [
            dbc.Col(html.Span(label, className="text-muted small"), width=5),
            dbc.Col(html.Span(f"{value} {unit}", className="fw-bold small"), width=7),
        ],
        className="mb-1",
    )


def _pd_from_records(records):
    """Convert dcc.Store records back to DataFrame."""
    import pandas as pd

    return pd.DataFrame(records)


def import_isnan(v):
    """Check if value is NaN."""
    import math

    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    app = create_app()
    print("\n  KEK Power Competitiveness Dashboard")
    print("  http://127.0.0.1:8050/\n")
    app.run(debug=True, port=8050)


if __name__ == "__main__":
    main()
