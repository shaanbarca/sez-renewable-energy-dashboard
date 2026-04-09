"""KEK Power Competitiveness Dashboard — Plotly Dash application.

Map-forward layout with dash-mantine-components (DMC).
Two states: National View (default) and Zoomed KEK.

Usage:
    uv run python -m src.dash.app
"""

from __future__ import annotations

import os

import dash_leaflet as dl
import dash_mantine_components as dmc
from dotenv import load_dotenv

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from src.dash.constants import (
    ACTION_FLAG_COLORS,
    ACTION_FLAG_DESCRIPTIONS,
    ACTION_FLAG_LABELS,
    INFRA_INSIDE_SEZ_COLOR,
    INFRA_OUTSIDE_SEZ_COLOR,
    MAP_CENTER,
    MAP_ZOOM,
    NEAREST_SUBSTATION_COLOR,
    RUPTL_REGION_COLORS,
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
    load_kek_infrastructure,
    prepare_resource_df,
)
from src.dash.logic import (
    UserAssumptions,
    UserThresholds,
    compute_scorecard_live,
    get_default_assumptions,
    get_default_thresholds,
)
from src.dash.map_layers import (
    filter_substations_near_point,
    get_all_layers,
    get_kek_polygon_by_id,
    polygon_bbox,
)

load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

# ---------------------------------------------------------------------------
# Module-level data (loaded once at startup, never changes)
# ---------------------------------------------------------------------------

_DATA: dict | None = None
_RESOURCE_DF = None
_RUPTL_METRICS = None
_DEMAND_DF = None
_GRID_DF = None
_INFRA_MARKERS: dict[str, list[dict]] = {}


def _load_data():
    """Load and cache all pipeline data at module level."""
    global _DATA, _RESOURCE_DF, _RUPTL_METRICS, _DEMAND_DF, _GRID_DF, _INFRA_MARKERS
    if _DATA is not None:
        return

    _DATA = load_all_data()
    _RESOURCE_DF = prepare_resource_df(_DATA)
    _RUPTL_METRICS = compute_ruptl_region_metrics(_DATA["fct_ruptl_pipeline"])
    _DEMAND_DF = _DATA["fct_kek_demand"]
    _GRID_DF = _DATA["fct_grid_cost_proxy"]
    _INFRA_MARKERS = load_kek_infrastructure()

    # Pre-load map layers (rasters are downsampled and cached as base64 PNGs)
    get_all_layers()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgba(hex_color: str, alpha: float = 0.1) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _fmt_pct(v):
    if v is None or _is_nan_safe(v):
        return "---"
    return f"{v:.1%}"


def _is_nan_safe(v):
    import math

    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


def _pd_from_records(records):
    import pandas as pd

    return pd.DataFrame(records)


def _val_fn(kek):
    """Return a value formatter bound to a KEK row."""

    def _val(col, fmt=".2f"):
        v = kek.get(col)
        if v is None or (isinstance(v, float) and _is_nan_safe(v)):
            return "---"
        return f"{v:{fmt}}"

    return _val


def _row(label, value, unit):
    """Build a single scorecard data row."""
    return html.Div(
        [
            html.Span(
                label,
                style={
                    "color": "#aaa",
                    "fontSize": "12px",
                    "width": "45%",
                    "display": "inline-block",
                },
            ),
            html.Span(
                f"{value} {unit}",
                style={"fontWeight": "bold", "fontSize": "12px"},
            ),
        ],
        style={"marginBottom": "4px"},
    )


# ---------------------------------------------------------------------------
# Layout builders
# ---------------------------------------------------------------------------


def _build_assumptions_card():
    """Compact assumptions summary card with expandable sliders."""
    defaults = get_default_assumptions()
    default_thresholds = get_default_thresholds()

    def _slider(slider_id, config, default_val):
        label_text = f"{config['label']} ({config['unit']})" if config["unit"] else config["label"]
        return html.Div(
            [
                html.Div(
                    [
                        html.Span(label_text, style={"fontSize": "11px", "fontWeight": "bold"}),
                        dmc.Tooltip(
                            label=config.get("description", ""),
                            children=dmc.Badge(
                                "?",
                                size="xs",
                                variant="light",
                                style={"cursor": "help", "marginLeft": "4px"},
                            ),
                            position="top",
                            withArrow=True,
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "4px"},
                ),
                dcc.Slider(
                    id=slider_id,
                    min=config["min"],
                    max=config["max"],
                    step=config["step"],
                    value=default_val,
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True},
                ),
            ],
            style={"marginBottom": "12px"},
        )

    # Compact summary (always visible)
    summary = html.Div(
        [
            html.Div(
                "Assumptions",
                style={"fontWeight": "bold", "fontSize": "13px", "marginBottom": "8px"},
            ),
            html.Div(
                [
                    html.Span("WACC ", style={"color": "#aaa", "fontSize": "11px"}),
                    html.Span(
                        id="summary-wacc",
                        children=f"{defaults.wacc_pct}%",
                        style={"fontWeight": "bold", "fontSize": "11px"},
                    ),
                ],
                style={"marginBottom": "2px"},
            ),
            html.Div(
                [
                    html.Span("CAPEX ", style={"color": "#aaa", "fontSize": "11px"}),
                    html.Span(
                        id="summary-capex",
                        children=f"{defaults.capex_usd_per_kw} $/kW",
                        style={"fontWeight": "bold", "fontSize": "11px"},
                    ),
                ],
                style={"marginBottom": "2px"},
            ),
            html.Div(
                [
                    html.Span("Lifetime ", style={"color": "#aaa", "fontSize": "11px"}),
                    html.Span(
                        id="summary-lifetime",
                        children=f"{defaults.lifetime_yr} years",
                        style={"fontWeight": "bold", "fontSize": "11px"},
                    ),
                ],
                style={"marginBottom": "2px"},
            ),
            html.Div(
                [
                    html.Span("Fixed O&M ", style={"color": "#aaa", "fontSize": "11px"}),
                    html.Span(
                        id="summary-fom",
                        children=f"{defaults.fom_usd_per_kw_yr} $/kW-yr",
                        style={"fontWeight": "bold", "fontSize": "11px"},
                    ),
                ],
                style={"marginBottom": "4px"},
            ),
        ],
    )

    # Expandable slider panels
    tier1_sliders = html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("WACC (%)", style={"fontSize": "11px", "fontWeight": "bold"}),
                            dmc.Tooltip(
                                label=WACC_DESCRIPTION,
                                children=dmc.Badge(
                                    "?",
                                    size="xs",
                                    variant="light",
                                    style={"cursor": "help", "marginLeft": "4px"},
                                ),
                                position="top",
                                withArrow=True,
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "marginBottom": "4px"},
                    ),
                    dcc.Slider(
                        id="slider-wacc",
                        min=WACC_MIN,
                        max=WACC_MAX,
                        step=WACC_STEP,
                        value=WACC_DEFAULT,
                        marks=WACC_MARKS,
                    ),
                ],
                style={"marginBottom": "12px"},
            ),
            _slider("slider-capex", TIER1_SLIDERS["capex_usd_per_kw"], defaults.capex_usd_per_kw),
            _slider("slider-lifetime", TIER1_SLIDERS["lifetime_yr"], defaults.lifetime_yr),
        ]
    )

    tier2_items = [
        _slider(f"slider-{k}", cfg, getattr(defaults, k)) for k, cfg in TIER2_SLIDERS.items()
    ]
    tier3_items = [
        _slider(f"slider-{k}", cfg, getattr(default_thresholds, k))
        for k, cfg in TIER3_SLIDERS.items()
    ]

    expand_content = html.Div(
        [
            html.Div(
                "Core Assumptions",
                style={
                    "fontWeight": "bold",
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "color": "#90CAF9",
                },
            ),
            tier1_sliders,
            html.Hr(style={"borderColor": "#444", "margin": "8px 0"}),
            html.Div(
                "Grid Cost Benchmark",
                style={"fontWeight": "bold", "fontSize": "11px", "marginBottom": "4px"},
            ),
            dmc.SegmentedControl(
                id="radio-grid-benchmark",
                data=[
                    {"label": "I-4/TT Tariff", "value": "tariff"},
                    {"label": "Regional BPP", "value": "bpp"},
                ],
                value="tariff",
                size="xs",
                style={"marginBottom": "12px"},
            ),
            html.Hr(style={"borderColor": "#444", "margin": "8px 0"}),
            dmc.Accordion(
                children=[
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl(
                                "Advanced Assumptions",
                                style={"fontSize": "11px", "padding": "4px 8px"},
                            ),
                            dmc.AccordionPanel(html.Div(tier2_items)),
                        ],
                        value="tier2",
                    ),
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl(
                                "Flag Thresholds", style={"fontSize": "11px", "padding": "4px 8px"}
                            ),
                            dmc.AccordionPanel(html.Div(tier3_items)),
                        ],
                        value="tier3",
                    ),
                ],
                variant="separated",
                chevronPosition="left",
            ),
            html.Hr(style={"borderColor": "#444", "margin": "8px 0"}),
            dmc.Button("Reset to Defaults", id="btn-reset", variant="subtle", size="xs"),
        ],
        style={"maxHeight": "60vh", "overflowY": "auto"},
    )

    return dmc.Paper(
        [
            summary,
            dmc.Collapse(
                expand_content,
                id="collapse-assumptions",
                opened=False,
            ),
            dmc.Button(
                "Expand",
                id="btn-expand-assumptions",
                variant="subtle",
                size="xs",
                fullWidth=True,
                style={"marginTop": "4px"},
            ),
        ],
        shadow="md",
        p="sm",
        style={
            "position": "absolute",
            "top": "60px",
            "left": "12px",
            "zIndex": 1000,
            "width": "340px",
            "maxHeight": "calc(85vh - 80px)",
            "overflowY": "auto",
            "backgroundColor": "rgba(30,30,30,0.92)",
            "backdropFilter": "blur(8px)",
            "border": "1px solid #555",
            "borderRadius": "8px",
        },
    )


def _build_legend():
    """Action flag legend, horizontal inline strip for the header bar."""
    items = []
    for flag, color in ACTION_FLAG_COLORS.items():
        items.append(
            dmc.Tooltip(
                label=ACTION_FLAG_DESCRIPTIONS[flag],
                children=html.Div(
                    [
                        html.Span(
                            "\u25cf",
                            style={"color": color, "fontSize": "12px", "marginRight": "3px"},
                        ),
                        html.Span(
                            ACTION_FLAG_LABELS[flag],
                            style={"fontSize": "10px", "color": "#ccc"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "cursor": "default"},
                ),
                position="bottom",
                withArrow=True,
                multiline=True,
                w=250,
            )
        )
    return html.Div(
        items,
        style={
            "display": "flex",
            "gap": "12px",
            "alignItems": "center",
            "marginLeft": "auto",
            "padding": "4px 12px",
            "border": "1px solid #555",
            "borderRadius": "6px",
            "backgroundColor": "rgba(40,40,40,0.8)",
        },
    )


def _build_table():
    """Ranked table for the bottom drawer."""
    return html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Filter by action flag:", style={"fontSize": "12px", "marginRight": "8px"}
                    ),
                    dcc.Dropdown(
                        id="filter-action-flag",
                        options=[{"label": v, "value": k} for k, v in ACTION_FLAG_LABELS.items()],
                        multi=True,
                        placeholder="All flags",
                        style={"width": "300px", "fontSize": "12px"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
            ),
            dash.dash_table.DataTable(
                id="ranked-table",
                columns=[{"name": v, "id": k} for k, v in TABLE_COLUMNS.items()],
                sort_action="native",
                page_size=15,
                export_format="csv",
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "10px 12px",
                    "fontSize": "13px",
                    "backgroundColor": "transparent",
                    "color": "#e0e0e0",
                    "border": "none",
                    "borderBottom": "1px solid #2a2a2a",
                    "fontFamily": "-apple-system, BlinkMacSystemFont, sans-serif",
                },
                style_header={
                    "fontWeight": "600",
                    "backgroundColor": "transparent",
                    "color": "#999",
                    "border": "none",
                    "borderBottom": "1px solid #444",
                    "fontSize": "11px",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.5px",
                },
                style_data_conditional=[
                    {
                        "if": {
                            "filter_query": '{action_flag} contains "'
                            + ACTION_FLAG_LABELS[flag]
                            + '"',
                            "column_id": "action_flag",
                        },
                        "color": color,
                        "fontWeight": "600",
                    }
                    for flag, color in ACTION_FLAG_COLORS.items()
                ],
            ),
            html.Div(
                id="table-empty-msg",
                children=html.P(
                    "No KEKs match the current filter. Try adjusting the action flag selection.",
                    style={"color": "#888", "textAlign": "center", "marginTop": "12px"},
                ),
                style={"display": "none"},
            ),
        ]
    )


def _build_quadrant():
    """Quadrant chart for the bottom drawer."""
    return dcc.Graph(id="quadrant-graph", style={"height": "100%"})


def _build_ruptl_chart():
    """RUPTL Context chart for the bottom drawer."""
    return html.Div(
        [
            html.Div(
                [
                    dmc.Select(
                        id="ruptl-region-filter",
                        label="Region",
                        data=[{"label": r, "value": r} for r in RUPTL_REGION_COLORS],
                        value=None,
                        placeholder="All regions",
                        clearable=True,
                        size="xs",
                        style={"width": "180px"},
                    ),
                    dmc.SegmentedControl(
                        id="ruptl-scenario-toggle",
                        data=[
                            {"label": "RE Base", "value": "re_base"},
                            {"label": "ARED", "value": "ared"},
                            {"label": "Both", "value": "both"},
                        ],
                        value="both",
                        size="xs",
                        style={"marginLeft": "12px"},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "flex-end",
                    "marginBottom": "8px",
                    "gap": "8px",
                },
            ),
            dcc.Graph(id="ruptl-graph", style={"height": "calc(100% - 60px)"}),
        ],
        style={"height": "100%"},
    )


def _build_bottom_drawer():
    """Translucent bottom drawer with Table/Quadrant/RUPTL/Flip tabs."""
    return html.Div(
        [
            # Grab handle
            html.Div(
                html.Div(
                    style={
                        "width": "40px",
                        "height": "4px",
                        "backgroundColor": "#666",
                        "borderRadius": "2px",
                        "margin": "0 auto",
                    },
                ),
                id="drawer-handle",
                style={"padding": "6px 0", "cursor": "pointer", "textAlign": "center"},
            ),
            # Tabs
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [
                            dmc.TabsTab("Table", value="table"),
                            dmc.TabsTab("Quadrant Chart", value="quadrant"),
                            dmc.TabsTab("RUPTL", value="ruptl"),
                            dmc.TabsTab("Flip Scenario", value="flip"),
                        ],
                    ),
                    dmc.TabsPanel(
                        _build_table(),
                        value="table",
                        style={
                            "height": "calc(40vh - 80px)",
                            "overflowY": "auto",
                            "padding": "8px 0",
                        },
                    ),
                    dmc.TabsPanel(
                        _build_quadrant(),
                        value="quadrant",
                        style={"height": "calc(40vh - 80px)", "padding": "8px 0"},
                    ),
                    dmc.TabsPanel(
                        _build_ruptl_chart(),
                        value="ruptl",
                        style={"height": "calc(40vh - 80px)", "padding": "8px 0"},
                    ),
                    dmc.TabsPanel(
                        html.Div(
                            "Flip Scenario — coming soon",
                            style={"color": "#888", "padding": "24px", "textAlign": "center"},
                        ),
                        value="flip",
                        style={"height": "calc(40vh - 80px)", "padding": "8px 0"},
                    ),
                ],
                value="table",
                color="blue",
            ),
        ],
        id="bottom-drawer",
        style={
            "position": "fixed",
            "bottom": 0,
            "left": 0,
            "right": 0,
            "height": "40vh",
            "backgroundColor": "rgba(20,20,20,0.92)",
            "backdropFilter": "blur(12px)",
            "borderTop": "1px solid #444",
            "zIndex": 900,
            "padding": "0 16px 8px 16px",
            "overflowY": "auto",
            "transition": "height 0.3s ease",
        },
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> dash.Dash:
    """Create and configure the Dash application."""
    try:
        _load_data()
    except DataLoadError as e:
        app = dash.Dash(__name__)
        app.layout = dmc.MantineProvider(
            dmc.Alert(
                title="Data not found",
                children=str(e),
                color="red",
                style={"margin": "24px"},
            ),
            theme={"colorScheme": "dark"},
        )
        return app

    app = dash.Dash(__name__, suppress_callback_exceptions=True)

    # --- Layout ---
    app.layout = dmc.MantineProvider(
        html.Div(
            [
                # Stores
                dcc.Store(id="user-assumptions", data=get_default_assumptions().to_dict()),
                dcc.Store(id="user-thresholds", data=get_default_thresholds().to_dict()),
                dcc.Store(id="selected-kek", data=None),
                dcc.Store(id="scorecard-live-data", data=None),
                dcc.Store(id="drawer-open", data=True),
                # Loading overlay
                dcc.Loading(
                    id="loading-overlay",
                    type="default",
                    fullscreen=True,
                    children=html.Div(id="loading-trigger"),
                ),
                # Header bar
                html.Div(
                    [
                        html.Span(
                            "Indonesia KEK Power Competitiveness",
                            style={"fontWeight": "bold", "fontSize": "16px"},
                        ),
                        dmc.SegmentedControl(
                            id="energy-toggle",
                            data=[
                                {"label": "Solar", "value": "solar"},
                                {"label": "Wind", "value": "wind"},
                                {"label": "Overall", "value": "overall"},
                            ],
                            value="solar",
                            size="xs",
                            style={"marginLeft": "16px"},
                        ),
                        _build_legend(),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "padding": "10px 16px",
                        "backgroundColor": "#1a1a1a",
                        "borderBottom": "1px solid #333",
                        "position": "fixed",
                        "top": 0,
                        "left": 0,
                        "right": 0,
                        "zIndex": 1100,
                        "height": "48px",
                    },
                ),
                # Map (full-screen, behind everything)
                html.Div(
                    [
                        dl.Map(
                            id="leaflet-map",
                            center=[MAP_CENTER["lat"], MAP_CENTER["lon"]],
                            zoom=MAP_ZOOM,
                            zoomControl=False,
                            style={"height": "100%", "width": "100%", "backgroundColor": "#121212"},
                            children=[
                                dl.TileLayer(
                                    url=(
                                        "https://api.mapbox.com/styles/v1/mapbox/dark-v11"
                                        "/tiles/{z}/{x}/{y}@2x"
                                        f"?access_token={MAPBOX_TOKEN}"
                                    ),
                                    attribution=(
                                        '&copy; <a href="https://www.mapbox.com/">Mapbox</a>'
                                    ),
                                    tileSize=512,
                                    zoomOffset=-1,
                                ),
                                dl.ZoomControl(position="topright"),
                            ],
                        ),
                        # Back button (visible in zoomed KEK state)
                        dmc.Button(
                            "Back to National View",
                            id="back-to-national",
                            variant="filled",
                            color="dark",
                            size="xs",
                            style={
                                "position": "absolute",
                                "top": "10px",
                                "left": "50%",
                                "transform": "translateX(-50%)",
                                "zIndex": 1000,
                                "display": "none",
                            },
                        ),
                        _build_assumptions_card(),
                    ],
                    style={
                        "position": "fixed",
                        "top": "48px",
                        "left": 0,
                        "right": 0,
                        "bottom": 0,
                    },
                ),
                # Scorecard side panel (right drawer, hidden by default)
                dmc.Drawer(
                    id="scorecard-drawer",
                    title="KEK Scorecard",
                    position="right",
                    size="380px",
                    opened=False,
                    closeOnClickOutside=True,
                    withOverlay=False,
                    styles={
                        "body": {"backgroundColor": "rgba(20,20,20,0.95)", "color": "#e0e0e0"},
                        "header": {
                            "backgroundColor": "rgba(20,20,20,0.95)",
                            "color": "#e0e0e0",
                            "borderBottom": "1px solid #333",
                        },
                        "close": {"color": "#e0e0e0", "width": "28px", "height": "28px"},
                    },
                    children=[
                        html.Div(
                            id="scorecard-kek-name",
                            style={"fontWeight": "bold", "fontSize": "16px", "marginBottom": "8px"},
                        ),
                        html.Div(id="scorecard-body"),
                    ],
                ),
                # Bottom drawer
                _build_bottom_drawer(),
            ],
            style={
                "backgroundColor": "#121212",
                "color": "#e0e0e0",
                "height": "100vh",
                "overflow": "hidden",
            },
        ),
        theme={"colorScheme": "dark"},
    )

    _register_callbacks(app)
    return app


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


def _register_callbacks(app: dash.Dash):
    # Toggle assumptions expand/collapse
    @app.callback(
        [Output("collapse-assumptions", "opened"), Output("btn-expand-assumptions", "children")],
        Input("btn-expand-assumptions", "n_clicks"),
        State("collapse-assumptions", "opened"),
        prevent_initial_call=True,
    )
    def toggle_assumptions(n, opened):
        new_state = not opened
        return new_state, "Collapse" if new_state else "Expand"

    # Toggle bottom drawer
    @app.callback(
        Output("bottom-drawer", "style"),
        Input("drawer-handle", "n_clicks"),
        State("drawer-open", "data"),
        prevent_initial_call=True,
    )
    def toggle_drawer(n, is_open):
        base_style = {
            "position": "fixed",
            "bottom": 0,
            "left": 0,
            "right": 0,
            "backgroundColor": "rgba(20,20,20,0.92)",
            "backdropFilter": "blur(12px)",
            "borderTop": "1px solid #444",
            "zIndex": 900,
            "padding": "0 16px 8px 16px",
            "overflowY": "auto",
            "transition": "height 0.3s ease",
        }
        if is_open:
            base_style["height"] = "32px"
        else:
            base_style["height"] = "40vh"
        return base_style

    @app.callback(
        Output("drawer-open", "data"),
        Input("drawer-handle", "n_clicks"),
        State("drawer-open", "data"),
        prevent_initial_call=True,
    )
    def update_drawer_state(n, is_open):
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

    # Summary card display update
    @app.callback(
        [
            Output("summary-wacc", "children"),
            Output("summary-capex", "children"),
            Output("summary-lifetime", "children"),
            Output("summary-fom", "children"),
        ],
        Input("user-assumptions", "data"),
    )
    def update_summary(data):
        a = UserAssumptions.from_dict(data)
        return (
            f"{a.wacc_pct}%",
            f"{a.capex_usd_per_kw} $/kW",
            f"{a.lifetime_yr} years",
            f"{a.fom_usd_per_kw_yr} $/kW-yr",
        )

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
            [d.wacc_pct, d.capex_usd_per_kw, d.lifetime_yr]
            + [getattr(d, k) for k in TIER2_SLIDERS]
            + [getattr(t, k) for k in TIER3_SLIDERS]
        )

    # Live recomputation
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

    # Map (dash-leaflet) — updates children + viewport on the persistent dl.Map
    @app.callback(
        [
            Output("leaflet-map", "children"),
            Output("leaflet-map", "viewport"),
            Output("back-to-national", "style"),
        ],
        [
            Input("scorecard-live-data", "data"),
            Input("selected-kek", "data"),
        ],
    )
    def update_map(scorecard_data, selected_kek):
        if not scorecard_data:
            scorecard = _DATA["fct_kek_scorecard"]
        else:
            scorecard = _pd_from_records(scorecard_data)
            dim = _DATA["dim_kek"][["kek_id", "kek_name", "latitude", "longitude"]]
            for col in dim.columns:
                if col != "kek_id" and col not in scorecard.columns:
                    scorecard = scorecard.merge(dim[["kek_id", col]], on="kek_id", how="left")

        map_layers = get_all_layers()

        # Base tile layer stays in layout; only dynamic children here
        tile_layer = dl.TileLayer(
            url=(
                "https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{z}/{x}/{y}@2x"
                f"?access_token={MAPBOX_TOKEN}"
            ),
            attribution='&copy; <a href="https://www.mapbox.com/">Mapbox</a>',
            tileSize=512,
            zoomOffset=-1,
        )

        # --- Overlay layers for LayersControl ---
        overlay_children = []

        # Substations overlay (national view only)
        if map_layers.get("substations") and not selected_kek:
            subs = map_layers["substations"]
            sub_markers = [
                dl.CircleMarker(
                    center=[s["lat"], s["lon"]],
                    radius=3,
                    color="#666666",
                    fillColor="#666666",
                    fillOpacity=0.6,
                    weight=1,
                    children=dl.Tooltip(f"{s['name']} | {s['voltage']} | {s['capacity_mva']} MVA"),
                )
                for s in subs
            ]
            overlay_children.append(
                dl.Overlay(
                    dl.LayerGroup(sub_markers),
                    name="Substations (PLN)",
                    checked=False,
                )
            )

        # KEK boundary polygons overlay (national view only)
        if map_layers.get("kek_polygons") and not selected_kek:
            overlay_children.append(
                dl.Overlay(
                    dl.GeoJSON(
                        data=map_layers["kek_polygons"],
                        style={"color": "#E91E63", "weight": 2, "fillOpacity": 0},
                        hoverStyle={"weight": 4, "color": "#FF4081"},
                    ),
                    name="KEK Boundaries",
                    checked=False,
                )
            )

        # Raster overlays
        raster_defs = [
            ("pvout", "Solar Potential (PVOUT)"),
            ("buildable", "Buildable Solar Area"),
            ("wind", "Wind Speed (100m)"),
        ]
        for layer_key, label in raster_defs:
            if map_layers.get(layer_key):
                b64_png, coordinates = map_layers[layer_key]
                # coordinates format: [[lon_min, lat_max], [lon_max, lat_max],
                #                      [lon_max, lat_min], [lon_min, lat_min]]
                bounds = [
                    [coordinates[3][1], coordinates[3][0]],  # [lat_min, lon_min]
                    [coordinates[0][1], coordinates[1][0]],  # [lat_max, lon_max]
                ]
                overlay_children.append(
                    dl.Overlay(
                        dl.ImageOverlay(url=b64_png, bounds=bounds, opacity=0.7),
                        name=label,
                        checked=False,
                    )
                )

        # Peatland overlay
        if map_layers.get("peatland") and not selected_kek:
            overlay_children.append(
                dl.Overlay(
                    dl.GeoJSON(
                        data=map_layers["peatland"],
                        style={
                            "color": "#8B4513",
                            "weight": 1,
                            "fillColor": "#8B4513",
                            "fillOpacity": 0.3,
                        },
                    ),
                    name="Peatland",
                    checked=False,
                )
            )

        # Protected forest (kawasan hutan) overlay
        if map_layers.get("protected_forest") and not selected_kek:
            overlay_children.append(
                dl.Overlay(
                    dl.GeoJSON(
                        data=map_layers["protected_forest"],
                        style={
                            "color": "#2E7D32",
                            "weight": 1,
                            "fillColor": "#2E7D32",
                            "fillOpacity": 0.25,
                        },
                    ),
                    name="Protected Forest",
                    checked=False,
                )
            )

        # Industrial facilities overlay
        if map_layers.get("industrial") and not selected_kek:
            ind_markers = [
                dl.CircleMarker(
                    center=[f["lat"], f["lon"]],
                    radius=2,
                    color="#FF9800",
                    fillColor="#FF9800",
                    fillOpacity=0.7,
                    weight=1,
                    children=dl.Tooltip(f"{f['name']} | {f['district']}, {f['province']}"),
                )
                for f in map_layers["industrial"]
            ]
            overlay_children.append(
                dl.Overlay(
                    dl.LayerGroup(ind_markers),
                    name="Industrial Facilities",
                    checked=False,
                )
            )

        # --- KEK action flag markers (always visible) ---
        kek_markers = []
        if "action_flag" in scorecard.columns:
            for _, row in scorecard.iterrows():
                flag = row.get("action_flag", "")
                color = ACTION_FLAG_COLORS.get(flag, "#888")
                label = ACTION_FLAG_LABELS.get(flag, flag)
                kek_id = row.get("kek_id", "")
                kek_name = row.get("kek_name", kek_id)
                lat = row.get("latitude")
                lon = row.get("longitude")
                if lat is None or lon is None:
                    continue

                is_selected = selected_kek and kek_id == selected_kek
                kek_markers.append(
                    dl.CircleMarker(
                        id={"type": "kek-marker", "kek_id": kek_id},
                        center=[float(lat), float(lon)],
                        radius=14 if is_selected else 8,
                        color="#FFD600" if is_selected else color,
                        fillColor="#FFD600" if is_selected else color,
                        fillOpacity=0.5 if is_selected else 0.8,
                        weight=3 if is_selected else 2,
                        children=dl.Tooltip(f"{kek_name} ({label})"),
                        n_clicks=0,
                    )
                )

        # --- Zoomed KEK layers (State 2) ---
        zoomed_layers = []
        map_center = [MAP_CENTER["lat"], MAP_CENTER["lon"]]
        map_zoom = MAP_ZOOM

        if selected_kek:
            sel = (
                scorecard[scorecard["kek_id"] == selected_kek]
                if "kek_id" in scorecard.columns
                else None
            )

            # KEK polygon
            poly_feat = get_kek_polygon_by_id(selected_kek)
            if poly_feat:
                bbox = polygon_bbox(poly_feat)
                min_lon, min_lat, max_lon, max_lat, clat, clon = bbox
                map_center = [clat, clon]
                span = max(max_lat - min_lat, max_lon - min_lon)
                if span > 0:
                    import math

                    map_zoom = min(15, max(8, int(8 - math.log2(span))))
                else:
                    map_zoom = 12

                # Action flag color for polygon
                kek_flag = None
                if sel is not None and not sel.empty and "action_flag" in sel.columns:
                    kek_flag = sel.iloc[0].get("action_flag")
                poly_color = ACTION_FLAG_COLORS.get(kek_flag, "#E91E63")

                zoomed_layers.append(
                    dl.GeoJSON(
                        data={"type": "FeatureCollection", "features": [poly_feat]},
                        style={
                            "color": poly_color,
                            "weight": 2,
                            "fillColor": poly_color,
                            "fillOpacity": 0.15,
                        },
                    )
                )

            # Nearby substations
            if sel is not None and not sel.empty:
                kek_lat = float(sel.iloc[0]["latitude"])
                kek_lon = float(sel.iloc[0]["longitude"])
                nearby_subs = filter_substations_near_point(kek_lat, kek_lon, radius_km=50)

                nearest_name = None
                if "fct_substation_proximity" in _DATA:
                    prox = _DATA["fct_substation_proximity"]
                    prox_row = prox[prox["kek_id"] == selected_kek]
                    if not prox_row.empty:
                        nearest_name = prox_row.iloc[0].get("nearest_substation_name")

                for s in nearby_subs:
                    is_nearest = nearest_name and s["name"] == nearest_name
                    zoomed_layers.append(
                        dl.CircleMarker(
                            center=[s["lat"], s["lon"]],
                            radius=7 if is_nearest else 4,
                            color=NEAREST_SUBSTATION_COLOR if is_nearest else "#888",
                            fillColor=NEAREST_SUBSTATION_COLOR if is_nearest else "#888",
                            fillOpacity=0.9 if is_nearest else 0.6,
                            weight=2 if is_nearest else 1,
                            children=dl.Tooltip(
                                f"{s['name']} | {s['voltage']} | {s['capacity_mva']} MVA | {s['dist_km']} km"
                                + (" (Nearest)" if is_nearest else "")
                            ),
                        )
                    )

                # Infrastructure markers
                infra = _INFRA_MARKERS.get(selected_kek, [])
                for m in infra:
                    is_inside = "inside" in m["category"].lower()
                    color = INFRA_INSIDE_SEZ_COLOR if is_inside else INFRA_OUTSIDE_SEZ_COLOR
                    zoomed_layers.append(
                        dl.CircleMarker(
                            center=[m["lat"], m["lon"]],
                            radius=6,
                            color=color,
                            fillColor=color,
                            fillOpacity=0.8,
                            weight=2,
                            children=dl.Tooltip(
                                f"{m['title']} ({'Inside' if is_inside else 'Outside'} SEZ)"
                            ),
                        )
                    )

        # Build map children (tile layer + overlays + markers)
        map_children = [tile_layer]

        # Add LayersControl with overlays
        if overlay_children:
            map_children.append(dl.LayersControl(overlay_children, position="topright"))

        # Add KEK markers
        map_children.append(dl.LayerGroup(kek_markers))

        # Add zoomed KEK layers
        if zoomed_layers:
            map_children.append(dl.LayerGroup(zoomed_layers))

        # Viewport with flyTo transition
        viewport = dict(
            center=map_center,
            zoom=map_zoom,
            transition="flyTo",
        )

        # Back button visibility
        back_style = {
            "position": "absolute",
            "top": "10px",
            "left": "50%",
            "transform": "translateX(-50%)",
            "zIndex": 1000,
            "display": "block" if selected_kek else "none",
        }

        return map_children, viewport, back_style

    # Ranked table
    @app.callback(
        [Output("ranked-table", "data"), Output("table-empty-msg", "style")],
        [Input("scorecard-live-data", "data"), Input("filter-action-flag", "value")],
    )
    def update_table(scorecard_data, flag_filter):
        if not scorecard_data:
            df = _DATA["fct_kek_scorecard"]
        else:
            df = _pd_from_records(scorecard_data)
            precomputed = _DATA["fct_kek_scorecard"]
            merge_cols = [
                c for c in TABLE_COLUMNS if c not in df.columns and c in precomputed.columns
            ]
            if merge_cols:
                df = df.merge(precomputed[["kek_id"] + merge_cols], on="kek_id", how="left")
        if flag_filter and "action_flag" in df.columns:
            df = df[df["action_flag"].isin(flag_filter)]
        display_cols = [c for c in TABLE_COLUMNS if c in df.columns]
        records = df[display_cols].round(2).to_dict("records")
        # Replace raw action flag keys with "● Label" for colored dot display
        for rec in records:
            if "action_flag" in rec:
                raw = rec["action_flag"]
                label = ACTION_FLAG_LABELS.get(raw, raw)
                rec["action_flag"] = f"\u25cf {label}"
        empty_style = {"display": "block"} if len(records) == 0 else {"display": "none"}
        return records, empty_style

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

        grid_proxy = _DATA["fct_grid_cost_proxy"][
            ["grid_region_id", "bpp_usd_mwh", "dashboard_rate_usd_mwh"]
        ]
        if "grid_region_id" not in sc.columns:
            dim = _DATA["dim_kek"][["kek_id", "grid_region_id"]]
            sc = sc.merge(dim, on="kek_id", how="left")
        sc = sc.merge(grid_proxy, on="grid_region_id", how="left")

        if benchmark_mode == "bpp":
            sc["grid_cost_y"] = sc["bpp_usd_mwh"].fillna(sc["dashboard_rate_usd_mwh"])
            y_label = "PLN Generation Cost ($/MWh)"
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
            )
        )
        fig.add_shape(
            type="rect",
            x0=0,
            y0=0,
            x1=max_val,
            y1=max_val,
            fillcolor="rgba(46,125,50,0.06)",
            line=dict(width=0),
            layer="below",
        )
        fig.add_annotation(
            x=max_val * 0.15,
            y=max_val * 0.85,
            text="Solar Competitive",
            showarrow=False,
            font=dict(size=11, color="rgba(46,125,50,0.5)"),
        )
        fig.add_annotation(
            x=max_val * 0.85,
            y=max_val * 0.15,
            text="Grid Competitive",
            showarrow=False,
            font=dict(size=11, color="rgba(198,40,40,0.5)"),
        )

        fig.update_layout(
            xaxis_title="Solar LCOE ($/MWh)",
            yaxis_title=y_label,
            margin=dict(l=50, r=20, t=30, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,20,0.8)",
            font=dict(color="#e0e0e0"),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333"),
        )
        return fig

    # RUPTL Context chart
    @app.callback(
        Output("ruptl-graph", "figure"),
        [
            Input("scorecard-live-data", "data"),
            Input("ruptl-region-filter", "value"),
            Input("ruptl-scenario-toggle", "value"),
            Input("selected-kek", "data"),
        ],
    )
    def update_ruptl(scorecard_data, region_filter, scenario, selected_kek):
        import plotly.graph_objects as go

        ruptl = _DATA["fct_ruptl_pipeline"].copy()

        # Auto-filter to selected KEK's region
        selected_region = None
        if selected_kek:
            dim = _DATA["dim_kek"]
            kek_row = dim[dim["kek_id"] == selected_kek]
            if not kek_row.empty:
                selected_region = kek_row.iloc[0].get("grid_region_id")

        if region_filter:
            ruptl = ruptl[ruptl["grid_region_id"] == region_filter]
        elif selected_region:
            ruptl = ruptl[ruptl["grid_region_id"] == selected_region]

        fig = go.Figure()

        regions = ruptl["grid_region_id"].unique()
        for region in regions:
            rdf = ruptl[ruptl["grid_region_id"] == region]
            color = RUPTL_REGION_COLORS.get(region, "#888")

            if scenario in ("re_base", "both"):
                fig.add_trace(
                    go.Bar(
                        x=rdf["year"],
                        y=rdf["plts_new_mw_re_base"],
                        name=f"{region} (RE Base)",
                        marker_color=color,
                        opacity=1.0 if scenario == "re_base" else 0.8,
                        hovertemplate=f"<b>{region}</b><br>Year: %{{x}}<br>RE Base: %{{y}} MW<extra></extra>",
                    )
                )
            if scenario in ("ared", "both"):
                fig.add_trace(
                    go.Bar(
                        x=rdf["year"],
                        y=rdf["plts_new_mw_ared"],
                        name=f"{region} (ARED)",
                        marker_color=color,
                        opacity=0.5,
                        marker_pattern_shape="/",
                        hovertemplate=f"<b>{region}</b><br>Year: %{{x}}<br>ARED: %{{y}} MW<extra></extra>",
                    )
                )

        # 2030 threshold line
        fig.add_vline(
            x=2030.5,
            line_dash="dash",
            line_color="#888",
            annotation_text="2030 threshold",
            annotation_position="top",
        )

        # Annotation for selected KEK
        if selected_region and not region_filter:
            kek_name = selected_kek
            dim = _DATA["dim_kek"]
            kek_row = dim[dim["kek_id"] == selected_kek]
            if not kek_row.empty:
                kek_name = kek_row.iloc[0].get("kek_name", selected_kek)
            fig.add_annotation(
                text=f"{kek_name} is in {selected_region}",
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.98,
                showarrow=False,
                font=dict(size=11, color="#FFD600"),
                bgcolor="rgba(0,0,0,0.6)",
            )

        fig.update_layout(
            title="Planned Solar Capacity Additions (MW)",
            xaxis_title="Year",
            yaxis_title="MW of new PLTS",
            barmode="group",
            margin=dict(l=50, r=20, t=40, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(20,20,20,0.8)",
            font=dict(color="#e0e0e0"),
            xaxis=dict(gridcolor="#333", dtick=1),
            yaxis=dict(gridcolor="#333"),
            legend=dict(bgcolor="rgba(0,0,0,0.5)", font=dict(size=9)),
        )
        return fig

    # KEK marker click -> selected KEK + open scorecard drawer
    @app.callback(
        [Output("selected-kek", "data"), Output("scorecard-drawer", "opened")],
        Input({"type": "kek-marker", "kek_id": dash.ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def marker_click(n_clicks_list):
        if not any(n_clicks_list):
            return dash.no_update, dash.no_update
        ctx = dash.callback_context
        if ctx.triggered:
            prop_id = ctx.triggered[0]["prop_id"]
            # Parse the pattern-matching ID: {"type":"kek-marker","kek_id":"xxx"}.n_clicks
            import json

            try:
                id_str = prop_id.rsplit(".", 1)[0]
                marker_id = json.loads(id_str)
                kek_id = marker_id.get("kek_id")
                if kek_id:
                    return kek_id, True
            except (json.JSONDecodeError, KeyError):
                pass
        return dash.no_update, dash.no_update

    # Back to national view button
    @app.callback(
        [
            Output("selected-kek", "data", allow_duplicate=True),
            Output("scorecard-drawer", "opened", allow_duplicate=True),
        ],
        Input("back-to-national", "n_clicks"),
        prevent_initial_call=True,
    )
    def back_to_national(n_clicks):
        if n_clicks:
            return None, False
        return dash.no_update, dash.no_update

    # Table click -> selected KEK + open scorecard drawer
    @app.callback(
        [
            Output("selected-kek", "data", allow_duplicate=True),
            Output("scorecard-drawer", "opened", allow_duplicate=True),
        ],
        Input("ranked-table", "active_cell"),
        State("ranked-table", "data"),
        prevent_initial_call=True,
    )
    def table_click(active_cell, table_data):
        if active_cell and table_data:
            row = table_data[active_cell["row"]]
            kek_id = row.get("kek_id") if "kek_id" in row else row.get("kek_name")
            if kek_id:
                return kek_id, True
        return None, False

    # Close scorecard drawer -> clear selected KEK
    @app.callback(
        Output("selected-kek", "data", allow_duplicate=True),
        Input("scorecard-drawer", "opened"),
        prevent_initial_call=True,
    )
    def clear_kek_on_close(opened):
        if not opened:
            return None
        return dash.no_update

    # Scorecard panel content
    @app.callback(
        [Output("scorecard-body", "children"), Output("scorecard-kek-name", "children")],
        [Input("selected-kek", "data"), Input("scorecard-live-data", "data")],
    )
    def update_scorecard(selected_kek, scorecard_data):
        if not selected_kek:
            return html.P(
                "Click a KEK on the map or table to view details.", style={"color": "#888"}
            ), ""

        if scorecard_data:
            sc = _pd_from_records(scorecard_data)
        else:
            sc = _DATA["fct_kek_scorecard"]

        # Merge resource data
        resource_cols = [
            "kek_id",
            "pvout_centroid",
            "pvout_best_50km",
            "pvout_buildable_best_50km",
            "cf_centroid",
            "cf_best_50km",
            "buildable_area_ha",
            "max_captive_capacity_mwp",
        ]
        for col in resource_cols:
            if col != "kek_id" and col not in sc.columns and col in _RESOURCE_DF.columns:
                sc = sc.merge(_RESOURCE_DF[["kek_id", col]], on="kek_id", how="left")

        precomputed = _DATA["fct_kek_scorecard"]
        extra_cols = [
            "resource_quality",
            "demand_mwh_2030",
            "dist_to_nearest_substation_km",
            "nearest_substation_capacity_mva",
            "siting_scenario",
            "green_share_geas",
            "ruptl_summary",
            "grid_upgrade_pre2030",
            "post2030_share",
            "pre2030_solar_mw",
            "grid_emission_factor_t_co2_mwh",
        ]
        for col in extra_cols:
            if col not in sc.columns and col in precomputed.columns:
                sc = sc.merge(precomputed[["kek_id", col]], on="kek_id", how="left")

        kek_row = sc[sc["kek_id"] == selected_kek]
        if kek_row.empty:
            return html.P(
                f"KEK '{selected_kek}' not found.", style={"color": "#F57C00"}
            ), selected_kek

        kek = kek_row.iloc[0]
        kek_name = (
            _DATA["dim_kek"].set_index("kek_id").loc[selected_kek, "kek_name"]
            if selected_kek in _DATA["dim_kek"]["kek_id"].values
            else selected_kek
        )
        _val = _val_fn(kek)

        resource_panel = dmc.TabsPanel(
            html.Div(
                [
                    _row("PVOUT centroid", _val("pvout_centroid", ".0f"), "kWh/kWp"),
                    _row("PVOUT best 50km", _val("pvout_best_50km", ".0f"), "kWh/kWp"),
                    _row("PVOUT buildable", _val("pvout_buildable_best_50km", ".0f"), "kWh/kWp"),
                    _row("CF centroid", _fmt_pct(kek.get("cf_centroid")), ""),
                    _row("CF best 50km", _fmt_pct(kek.get("cf_best_50km")), ""),
                    _row("Buildable area", _val("buildable_area_ha", ".0f"), "ha"),
                    _row("Max captive cap", _val("max_captive_capacity_mwp", ".0f"), "MWp"),
                    _row("Resource quality", str(kek.get("resource_quality", "---")), ""),
                    _row("Project viable", str(kek.get("project_viable", "---")), ""),
                ],
                style={"marginTop": "8px"},
            ),
            value="resource",
        )

        lcoe_panel = dmc.TabsPanel(
            html.Div(
                [
                    _row(
                        "LCOE (low/mid/high)",
                        f"${_val('lcoe_low_usd_mwh')} / ${_val('lcoe_mid_usd_mwh')} / ${_val('lcoe_high_usd_mwh')}",
                        "/MWh",
                    ),
                    _row(
                        "Grid-connected",
                        f"${_val('lcoe_grid_connected_low_usd_mwh')} / ${_val('lcoe_grid_connected_usd_mwh')} / ${_val('lcoe_grid_connected_high_usd_mwh')}",
                        "/MWh",
                    ),
                    _row("Competitive gap", _val("solar_competitive_gap_pct", ".1f"), "%"),
                    _row("Solar Now", str(kek.get("solar_now", "---")), ""),
                    _row("Invest Resilience", str(kek.get("invest_resilience", "---")), ""),
                    _row("Carbon breakeven", _val("carbon_breakeven_usd_tco2", ".1f"), "$/tCO2"),
                ],
                style={"marginTop": "8px"},
            ),
            value="lcoe",
        )

        demand_panel = dmc.TabsPanel(
            html.Div(
                [
                    _row("Demand (2030)", _val("demand_mwh_2030", ",.0f"), "MWh"),
                    _row("GEAS green share", _fmt_pct(kek.get("green_share_geas")), ""),
                    _row("Nearest substation", _val("dist_to_nearest_substation_km", ".1f"), "km"),
                    _row(
                        "Substation capacity", _val("nearest_substation_capacity_mva", ".0f"), "MVA"
                    ),
                    _row("Siting scenario", str(kek.get("siting_scenario", "---")), ""),
                ],
                style={"marginTop": "8px"},
            ),
            value="demand",
        )

        pipeline_panel = dmc.TabsPanel(
            html.Div(
                [
                    _row("Grid upgrade pre-2030", str(kek.get("grid_upgrade_pre2030", "---")), ""),
                    _row("Pre-2030 solar", _val("pre2030_solar_mw", ".0f"), "MW"),
                    _row("Post-2030 share", _fmt_pct(kek.get("post2030_share")), ""),
                    _row("RUPTL summary", str(kek.get("ruptl_summary", "---")), ""),
                    _row(
                        "Grid emission factor",
                        _val("grid_emission_factor_t_co2_mwh", ".3f"),
                        "tCO2/MWh",
                    ),
                ],
                style={"marginTop": "8px"},
            ),
            value="pipeline",
        )

        flags_panel = dmc.TabsPanel(
            html.Div(
                [
                    _row("Action Flag", str(kek.get("action_flag", "---")), ""),
                    _row("Solar Now", str(kek.get("solar_now", "---")), ""),
                    _row("Grid First", str(kek.get("grid_first", "---")), ""),
                    _row("Firming Needed", str(kek.get("firming_needed", "---")), ""),
                    _row("Invest Resilience", str(kek.get("invest_resilience", "---")), ""),
                    _row("Plan Late", str(kek.get("plan_late", "---")), ""),
                ],
                style={"marginTop": "8px"},
            ),
            value="flags",
        )

        body = dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Resource", value="resource"),
                        dmc.TabsTab("LCOE", value="lcoe"),
                        dmc.TabsTab("Demand", value="demand"),
                        dmc.TabsTab("Pipeline", value="pipeline"),
                        dmc.TabsTab("Flags", value="flags"),
                    ]
                ),
                resource_panel,
                lcoe_panel,
                demand_panel,
                pipeline_panel,
                flags_panel,
            ],
            value="resource",
            color="blue",
        )
        return body, kek_name


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    app = create_app()
    print("\n  KEK Power Competitiveness Dashboard")
    print("  http://127.0.0.1:8050/\n")
    app.run(debug=True, dev_tools_ui=False, port=8050)


if __name__ == "__main__":
    main()
