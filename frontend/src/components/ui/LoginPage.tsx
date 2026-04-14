import { useState } from 'react';

interface LoginPageProps {
  onSuccess: () => void;
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (data.ok) {
        onSuccess();
      } else {
        setError(data.error || 'Invalid access code');
      }
    } catch {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-[#0a0a0c]">
      <div
        className="w-full max-w-sm rounded-xl px-8 py-10"
        style={{
          background: 'rgba(20, 20, 24, 0.65)',
          backdropFilter: 'blur(32px) saturate(1.5)',
          WebkitBackdropFilter: 'blur(32px) saturate(1.5)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        }}
      >
        <h1 className="text-lg font-semibold tracking-wide text-[#e0e0e0] mb-1">
          SEZ Renewable Energy Dashboard
        </h1>
        <p className="text-xs text-[#666] mb-8">Enter your access code to continue</p>

        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Access code"
            // biome-ignore lint/a11y/noAutofocus: login page input should auto-focus
            autoFocus
            className="w-full px-4 py-3 rounded-lg text-sm outline-none mb-4 transition-colors"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: error
                ? '1px solid rgba(239, 83, 80, 0.5)'
                : '1px solid rgba(255, 255, 255, 0.1)',
              color: '#e0e0e0',
            }}
            onFocus={(e) => {
              if (!error) e.currentTarget.style.borderColor = 'rgba(144, 202, 249, 0.4)';
            }}
            onBlur={(e) => {
              if (!error) e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            }}
          />

          {error && <p className="text-xs text-[#ef5350] mb-4">{error}</p>}

          <button
            type="submit"
            disabled={loading || !code.trim()}
            className="w-full py-3 rounded-lg text-sm font-medium transition-all cursor-pointer"
            style={{
              background:
                loading || !code.trim() ? 'rgba(255, 255, 255, 0.05)' : 'rgba(144, 202, 249, 0.15)',
              color: loading || !code.trim() ? '#666' : '#90caf9',
              border:
                loading || !code.trim()
                  ? '1px solid rgba(255, 255, 255, 0.05)'
                  : '1px solid rgba(144, 202, 249, 0.3)',
            }}
          >
            {loading ? 'Verifying...' : 'Enter'}
          </button>
        </form>
      </div>
    </div>
  );
}
