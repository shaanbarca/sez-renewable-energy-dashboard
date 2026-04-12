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

  if (visible.length === 0 && !showRadius) return null;

  return (
    <div
      className="absolute top-[120px] left-1/2 z-20 flex gap-2 items-start"
      style={{ transform: `translate(calc(-50% + ${dragPos.x}px), ${dragPos.y}px)` }}
    >
      {/* Drag handle */}
      {(visible.length > 0 || showRadius) && (
        <div
          className="flex gap-2 items-start cursor-grab active:cursor-grabbing"
          onMouseDown={onDragStart}
        >
          {visible.map(({ key, label, unit, min, max, gradient }) => (
            <div
              key={key}
              className="rounded-lg px-3 py-2"
              style={{
                backdropFilter: 'var(--blur)',
                WebkitBackdropFilter: 'var(--blur)',
                background: 'var(--glass)',
                border: '1px solid var(--glass-border)',
              }}
            >
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

          {/* 50km radius legend */}
          {showRadius && (
            <div
              className="rounded-lg px-3 py-2 flex items-center gap-2"
              style={{
                backdropFilter: 'var(--blur)',
                WebkitBackdropFilter: 'var(--blur)',
                background: 'var(--glass)',
                border: '1px solid var(--glass-border)',
              }}
            >
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
              <span className="text-[10px] text-zinc-400">50 km radius</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
