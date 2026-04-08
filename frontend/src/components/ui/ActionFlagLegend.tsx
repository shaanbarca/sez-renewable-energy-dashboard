import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';

const flags = Object.keys(ACTION_FLAG_COLORS);

export default function ActionFlagLegend() {
  return (
    <div className="flex items-center gap-4">
      {flags.map((flag) => (
        <div key={flag} className="flex items-center gap-1.5">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ backgroundColor: ACTION_FLAG_COLORS[flag] }}
          />
          <span className="text-xs text-zinc-400">{ACTION_FLAG_LABELS[flag]}</span>
        </div>
      ))}
    </div>
  );
}
