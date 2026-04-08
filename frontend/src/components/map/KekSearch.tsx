import { useCallback, useEffect, useRef, useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';

interface Props {
  onSelect: (kekId: string, lat: number, lon: number) => void;
}

export default function KekSearch({ onSelect }: Props) {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter KEKs by search query
  const results =
    scorecard?.filter((row) => row.kek_name.toLowerCase().includes(query.toLowerCase())) ?? [];

  const showDropdown = open && query.length > 0 && results.length > 0;

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = useCallback(
    (row: { kek_id: string; kek_name: string; latitude: number; longitude: number }) => {
      onSelect(row.kek_id, row.latitude, row.longitude);
      setQuery('');
      setOpen(false);
      inputRef.current?.blur();
    },
    [onSelect],
  );

  return (
    <div ref={containerRef} className="absolute top-3 left-3 z-10 w-64" data-search="kek">
      {/* Search input */}
      <div
        className="flex items-center gap-2 rounded-lg px-3 py-2"
        style={{
          backdropFilter: 'var(--blur)',
          WebkitBackdropFilter: 'var(--blur)',
          background: 'var(--glass)',
          border: '1px solid var(--glass-border)',
        }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-zinc-400 shrink-0"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search KEK..."
          className="bg-transparent text-xs text-zinc-200 placeholder-zinc-500 outline-none w-full"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setOpen(false);
            }}
            className="text-zinc-500 hover:text-zinc-300 text-xs cursor-pointer"
          >
            ✕
          </button>
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          className="mt-1 rounded-lg py-1 max-h-60 overflow-y-auto"
          style={{
            backdropFilter: 'blur(32px) saturate(1.5)',
            WebkitBackdropFilter: 'blur(32px) saturate(1.5)',
            background: 'rgba(20, 20, 24, 0.85)',
            border: '1px solid var(--glass-border)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            scrollbarWidth: 'thin',
            scrollbarColor: 'rgba(255,255,255,0.15) transparent',
          }}
        >
          {results.map((row) => (
            <button
              key={row.kek_id}
              onClick={() => handleSelect(row)}
              className="w-full text-left px-3 py-1.5 text-xs text-zinc-300 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
            >
              <div className="font-medium">{row.kek_name}</div>
              <div className="text-[10px] text-zinc-500">{row.province}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
