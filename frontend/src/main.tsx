import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './globals.css';
import { useDashboardStore } from './store/dashboard';

// Expose the Zustand store on window in dev mode so headless tooling
// (scripts/capture-console.mjs + future Playwright tests) can drive the app
// without DOM clicks. Stripped from production builds by Vite's `import.meta.env.DEV`.
if (import.meta.env.DEV) {
  (window as unknown as { useDashboardStore: typeof useDashboardStore }).useDashboardStore =
    useDashboardStore;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
