import { useDashboardStore } from '../../store/dashboard';

const RASTER_LEGENDS = [
  {
    key: 'pvout',
    label: 'PVOUT',
    unit: 'kWh/kWp/yr',
    min: '1,000',
    max: '1,800',
    gradient: 'linear-gradient(to right, #ffffb2, #fecc5c, #feb24c, #fd8d3c, #f03b20, #bd0026)',
  },
  {
    key: 'wind',
    label: 'Wind 100m',
    unit: 'm/s',
    min: '2',
    max: '8',
    gradient: 'linear-gradient(to right, #deebf7, #9ecae1, #6baed6, #4292c6, #2171b5, #084594)',
  },
] as const;

// Legend strip that sits directly below the Header. Full-width, thin, single
// row. Replaces the old floating center-top card — frees the ~100px of
// vertical map space the card used to occupy and collects every legend token
// in one consistent location. Renders null when there's nothing to show.
export default function RasterLegend() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const selectedSite = useDashboardStore((s) => s.selectedSite);

  const visible = RASTER_LEGENDS.filter(({ key }) => !!layerVisibility[key]);
  const showRadius = !!selectedSite;
  const showWindBuildable = !!layerVisibility.wind_buildable_polygons;
  const showSolarBuildable = !!layerVisibility.buildable_polygons;
  const hasSwatches = showRadius || showSolarBuildable || showWindBuildable;

  if (visible.length === 0 && !hasSwatches) return null;

  return (
    <div
      style={{
        // Strip is now rendered inside the header flex column (App.tsx), so
        // it naturally sits below the Header regardless of Header height.
        // No magic top offset — eliminates the coupling that broke when
        // typography changes grew the header by a few pixels.
        height: 32,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: '0 14px',
        // Darker glass — user flagged the header-bg value (3% white tint)
        // as too transparent against the dark map, text wasn't legible.
        // 0.85 alpha dark glass matches what we use on the V4 rail + pane.
        background: 'rgba(18, 18, 22, 0.85)',
        backdropFilter: 'blur(28px) saturate(1.4)',
        WebkitBackdropFilter: 'blur(28px) saturate(1.4)',
        borderBottom: '1px solid var(--glass-border-bright)',
        boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
        overflowX: 'auto',
        whiteSpace: 'nowrap',
      }}
    >
      {/* Raster gradients */}
      {visible.map(({ key, label, unit, min, max, gradient }, idx) => (
        <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          {idx > 0 && <Divider />}
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</span>
          <div style={{ height: 5, width: 80, borderRadius: 2, background: gradient }} />
          <span
            className="tnum"
            style={{ fontSize: 9, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}
          >
            {min}–{max} {unit}
          </span>
        </div>
      ))}

      {/* Spatial swatches — shown when a site is selected (shows the three
          zones on the map) or when a buildable layer is toggled standalone. */}
      {hasSwatches && (
        <>
          {visible.length > 0 && <Divider />}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
            {showRadius && (
              <>
                <Swatch color="#66BB6A" label="In-boundary solar" />
                <Swatch color="#4DD0E1" label="Remote solar (50 km)" />
                {showSolarBuildable && <Swatch color="#FFD54F" label="Chosen polygon" />}
                {showWindBuildable && <Swatch color="#7E57C2" label="Wind buildable" />}
                <Swatch color="#90CAF9" label="50 km radius" dashed />
              </>
            )}
            {!showRadius && showSolarBuildable && (
              <Swatch color="#4DD0E1" label="Solar buildable" />
            )}
            {!showRadius && showWindBuildable && <Swatch color="#7E57C2" label="Wind buildable" />}
          </div>
        </>
      )}
    </div>
  );
}

function Divider() {
  return (
    <span
      style={{
        width: 1,
        height: 14,
        background: 'var(--border-subtle)',
        flexShrink: 0,
      }}
    />
  );
}

function Swatch({
  color,
  label,
  dashed = false,
}: {
  color: string;
  label: string;
  dashed?: boolean;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: dashed ? '50%' : 2,
          background: `${color}44`,
          border: `1px ${dashed ? 'dashed' : 'solid'} ${color}`,
        }}
      />
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</span>
    </div>
  );
}
