import { useEffect, useRef, useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';

export default function ScenarioManager() {
  const savedScenarios = useDashboardStore((s) => s.savedScenarios);
  const saveScenario = useDashboardStore((s) => s.saveScenario);
  const loadScenario = useDashboardStore((s) => s.loadScenario);
  const deleteScenario = useDashboardStore((s) => s.deleteScenario);
  const recomputeScorecard = useDashboardStore((s) => s.recomputeScorecard);

  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (saving) inputRef.current?.focus();
  }, [saving]);

  const handleSave = () => {
    if (!name.trim()) return;
    saveScenario(name.trim());
    setName('');
    setSaving(false);
  };

  const handleLoad = async (id: string) => {
    loadScenario(id);
    await recomputeScorecard();
  };

  const atLimit = savedScenarios.length >= 3;

  return (
    <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-[10px] font-semibold uppercase tracking-wider"
          style={{ color: 'var(--text-muted)' }}
        >
          Scenarios
        </span>
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          {savedScenarios.length}/3
        </span>
      </div>

      {savedScenarios.length > 0 && (
        <div className="space-y-1.5 mb-2">
          {savedScenarios.map((s) => (
            <div
              key={s.id}
              className="flex items-center gap-2 px-2 py-1.5 rounded-md text-xs"
              style={{
                background: 'var(--card-bg)',
                border: '1px solid var(--card-border)',
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="truncate" style={{ color: 'var(--text-primary)' }}>
                  {s.name}
                </div>
                <div className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                  {new Date(s.createdAt).toLocaleDateString()}
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleLoad(s.id)}
                className="px-2 py-0.5 rounded text-[10px] font-medium transition-colors cursor-pointer"
                style={{
                  color: 'var(--accent)',
                  background: 'var(--accent-soft)',
                  border: '1px solid var(--accent-border)',
                }}
              >
                Load
              </button>
              <button
                type="button"
                onClick={() => deleteScenario(s.id)}
                className="p-0.5 rounded transition-colors cursor-pointer"
                style={{ color: 'var(--text-muted)' }}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {saving ? (
        <div className="flex gap-1.5">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value.slice(0, 30))}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
              if (e.key === 'Escape') {
                setSaving(false);
                setName('');
              }
            }}
            ref={inputRef}
            placeholder="Scenario name..."
            className="flex-1 px-2 py-1 rounded text-xs outline-none"
            style={{
              background: 'transparent',
              border: '1px solid var(--input-border)',
              color: 'var(--text-primary)',
            }}
          />
          <button
            type="button"
            onClick={handleSave}
            disabled={!name.trim()}
            className="px-2 py-1 rounded text-[10px] font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-default"
            style={{
              color: 'var(--accent)',
              background: 'var(--accent-soft)',
              border: '1px solid var(--accent-border)',
            }}
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setSaving(false);
              setName('');
            }}
            className="px-1.5 py-1 rounded text-[10px] transition-colors cursor-pointer"
            style={{ color: 'var(--text-muted)' }}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setSaving(true)}
          disabled={atLimit}
          className="w-full py-1.5 rounded text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-default"
          style={{
            color: atLimit ? 'var(--text-muted)' : 'var(--accent)',
            background: 'var(--accent-soft)',
            border: '1px solid var(--accent-border)',
          }}
        >
          {atLimit ? 'Limit Reached (3/3)' : 'Save Current Scenario'}
        </button>
      )}
    </div>
  );
}
