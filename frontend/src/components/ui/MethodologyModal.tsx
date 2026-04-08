import { useCallback, useEffect, useState } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fetchMethodology } from '../../lib/api';

interface MethodologyModalProps {
  open: boolean;
  onClose: () => void;
}

export default function MethodologyModal({ open, onClose }: MethodologyModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || content) return;
    fetchMethodology()
      .then(setContent)
      .catch((err) => setError(err.message));
  }, [open, content]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={handleBackdropClick}
      style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(8px)' }}
    >
      <div
        className="relative w-full max-w-4xl max-h-[85vh] rounded-2xl overflow-hidden flex flex-col"
        style={{
          background: 'rgba(24, 24, 28, 0.92)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 24px 80px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 shrink-0"
          style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}
        >
          <h2 className="text-lg font-semibold text-white">Methodology</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-white text-xl leading-none px-2 py-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto px-8 py-6 flex-1 methodology-content">
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {!content && !error && (
            <p className="text-zinc-500 text-sm animate-pulse">Loading methodology...</p>
          )}
          {content && (
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="text-2xl font-bold text-white mt-8 mb-4 first:mt-0">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-xl font-semibold text-white mt-8 mb-3">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-base font-semibold text-zinc-200 mt-6 mb-2">{children}</h3>
                ),
                h4: ({ children }) => (
                  <h4 className="text-sm font-semibold text-zinc-300 mt-4 mb-2">{children}</h4>
                ),
                p: ({ children }) => (
                  <p className="text-sm text-zinc-300 leading-relaxed mb-3">{children}</p>
                ),
                ul: ({ children }) => (
                  <ul className="text-sm text-zinc-300 list-disc pl-5 mb-3 space-y-1">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="text-sm text-zinc-300 list-decimal pl-5 mb-3 space-y-1">
                    {children}
                  </ol>
                ),
                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                a: ({ href, children }) => (
                  <a
                    href={href}
                    className="text-[#90CAF9] hover:text-white underline underline-offset-2"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
                code: ({ children, className }) => {
                  const isBlock = className?.includes('language-');
                  if (isBlock) {
                    return (
                      <code className="block bg-black/40 rounded-lg p-4 text-xs text-zinc-300 overflow-x-auto mb-3 font-mono">
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code className="bg-white/10 rounded px-1.5 py-0.5 text-xs text-[#90CAF9] font-mono">
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => <pre className="mb-3">{children}</pre>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-zinc-600 pl-4 my-3 text-zinc-400 italic text-sm">
                    {children}
                  </blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-4">
                    <table className="w-full text-xs text-zinc-300 border-collapse">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="border-b border-zinc-700 text-zinc-400">{children}</thead>
                ),
                th: ({ children }) => (
                  <th className="text-left px-3 py-2 font-medium">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 border-b border-zinc-800">{children}</td>
                ),
                hr: () => <hr className="border-zinc-700 my-6" />,
                strong: ({ children }) => (
                  <strong className="font-semibold text-zinc-100">{children}</strong>
                ),
                em: ({ children }) => <em className="text-zinc-400">{children}</em>,
              }}
            >
              {content}
            </Markdown>
          )}
        </div>
      </div>
    </div>
  );
}
