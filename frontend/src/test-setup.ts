/**
 * Vitest setup — polyfills browser-only APIs the store touches at module load.
 *
 * happy-dom v20+ stopped providing localStorage by default. The dashboard store
 * reads `localStorage.getItem('walkthrough_dismissed')` and `'kek_saved_scenarios'`
 * during `create()`, so we need an in-memory shim before the first import.
 */

class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  key(i: number): string | null {
    return Array.from(this.store.keys())[i] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
}

// Always override — happy-dom v20 ships a placeholder `localStorage` object
// without the `getItem` method (the new `--localstorage-file` flag is opt-in).
// The `typeof === 'undefined'` guard misses that case; explicitly replace.
Object.defineProperty(globalThis, 'localStorage', {
  value: new MemoryStorage(),
  writable: true,
  configurable: true,
});
Object.defineProperty(globalThis, 'sessionStorage', {
  value: new MemoryStorage(),
  writable: true,
  configurable: true,
});
