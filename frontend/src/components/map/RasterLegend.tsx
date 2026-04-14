import { useDraggable } from '../../hooks/useDraggable';
import { useDashboardStore } from '../../store/dashboard';

const RASTER_LEGENDS = [
  {
    key: 'pvout',
    label: 'Solar Potential (PVOUT)',
    unit: 'kWh/kWp/yr',
    min: '1,000',
    max: '1,800',
    gradient: 'linear-gradient(to right, #ffffb2, #fecc5c, #feb24c, #fd8d3c, #f03b20, #bd0026)',
  },
  {
    key: 'wind',
    label: 'Wind Speed (100m)',
    unit: 'm/s',
    min: '2',
    max: '8',
    gradient: 'linear-gradient(to right, #deebf7, #9ecae1, #6baed6, #4292c6, #2171b5, #084594)',
  },
] as const;

export default function RasterLegend() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const { position: dragPos, handleMouseDown: onDragStart } = useDraggable();

  const visible = RASTER_LEGENDS.filter(({ key }) => !!layerVisibility[key]);
  const showRadius = !!selectedKek;
  const showWindBuildable = !!layerVisibility.wind_buildable_polygons;
  const showSolarBuildable = !!layerVisibility.buildable_polygons;

  const hasSwatches = showRadius || (!showRadius && (showSolarBuildable || showWindBuildable));

  if (visible.length === 0 && !hasSwatches) return null;

  return (
    <div
      className="absolute top-[120px] left-1/2 z-20"
      style={{ transform: `translate(calc(-50% + ${dragPos.x}px), ${dragPos.y}px)` }}
    >
      <div
        className="rounded-lg px-3 py-2 cursor-grab active:cursor-grabbing"
        style={{
          backdropFilter: 'var(--blur)',
          WebkitBackdropFilter: 'var(--blur)',
          background: 'var(--glass)',
          border: '1px solid var(--glass-border)',
        }}
        onMouseDown={onDragStart}
      >
        {/* Row 1: Raster gradients side by side */}
        {visible.length > 0 && (
          <div className={`flex gap-4 justify-center ${hasSwatches ? 'mb-2' : ''}`}>
            {visible.map(({ key, label, unit, min, max, gradient }) => (
              <div key={key}>
                <div className="text-[10px] text-zinc-400 mb-1">
                  {label} <span className="text-zinc-600">({unit})</span>
                </div>
                <div className="h-3 rounded-sm w-48" style={{ background: gradient }} />
                <div className="flex justify-between mt-0.5">
                  <span className="text-[9px] text-zinc-500">{min}</span>
                  <span className="text-[9px] text-zinc-500">{max}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Row 2: Spatial legends when KEK is selected */}
        {showRadius && (
          <div className="flex items-center gap-3 flex-wrap justify-center">
            <div className="flex items-center gap-1.5">
              <svg width="14" height="14" viewBox="0 0 14 14">
                <rect
                  x="1"
                  y="1"
                  width="12"
                  height="12"
                  rx="2"
                  fill="rgba(102, 187, 106, 0.45)"
                  stroke="#43A047"
                  strokeWidth="1.5"
                />
              </svg>
              <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                In-boundary solar
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width="14" height="14" viewBox="0 0 14 14">
                <rect
                  x="1"
                  y="1"
                  width="12"
                  height="12"
                  rx="2"
                  fill="rgba(77, 208, 225, 0.35)"
                  stroke="#00ACC1"
                  strokeWidth="1.5"
                />
              </svg>
              <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                Remote solar (50 km)
              </span>
            </div>
            {showWindBuildable && (
              <>
                <div
                  className="h-4 mx-0.5"
                  style={{ width: 1, background: 'var(--border-subtle)' }}
                />
                <div className="flex items-center gap-1.5">
                  <svg width="14" height="14" viewBox="0 0 14 14">
                    <rect
                      x="1"
                      y="1"
                      width="12"
                      height="12"
                      rx="2"
                      fill="rgba(179, 157, 219, 0.4)"
                      stroke="#7E57C2"
                      strokeWidth="1.5"
                    />
                  </svg>
                  <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    Wind buildable
                  </span>
                </div>
              </>
            )}
            <div className="h-4 mx-0.5" style={{ width: 1, background: 'var(--border-subtle)' }} />
            <div className="flex items-center gap-1.5">
              <svg width="18" height="18" viewBox="0 0 18 18">
                <circle
                  cx="9"
                  cy="9"
                  r="7"
                  fill="rgba(144, 202, 249, 0.06)"
                  stroke="#90CAF9"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                  opacity="0.6"
                />
              </svg>
              <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                50 km radius
              </span>
            </div>
          </div>
        )}

        {/* Row 2: Standalone buildable legends when no KEK selected */}
        {!showRadius && (showSolarBuildable || showWindBuildable) && (
          <div className="flex items-center gap-3 justify-center">
            {showSolarBuildable && (
              <div className="flex items-center gap-1.5">
                <svg width="14" height="14" viewBox="0 0 14 14">
                  <rect
                    x="1"
                    y="1"
                    width="12"
                    height="12"
                    rx="2"
                    fill="rgba(77, 208, 225, 0.35)"
                    stroke="#00ACC1"
                    strokeWidth="1.5"
                  />
                </svg>
                <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  Solar Buildable
                </span>
              </div>
            )}
            {showWindBuildable && (
              <div className="flex items-center gap-1.5">
                <svg width="14" height="14" viewBox="0 0 14 14">
                  <rect
                    x="1"
                    y="1"
                    width="12"
                    height="12"
                    rx="2"
                    fill="rgba(179, 157, 219, 0.4)"
                    stroke="#7E57C2"
                    strokeWidth="1.5"
                  />
                </svg>
                <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  Wind Buildable
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
