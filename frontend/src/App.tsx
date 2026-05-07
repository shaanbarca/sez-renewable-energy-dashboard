import { useEffect } from 'react';
import MapHint from './components/map/MapHint';
import MapView from './components/map/MapView';
import RasterLegend from './components/map/RasterLegend';
import AssumptionsPanel from './components/panels/AssumptionsPanel';
import ScoreDrawer from './components/panels/ScoreDrawer';
import BottomPanel from './components/ui/BottomPanel';
import Header from './components/ui/Header';
// import LoginPage from './components/ui/LoginPage'; // re-enable when auth is re-enabled
import WalkthroughModal from './components/ui/WalkthroughModal';
import { useUrlSync } from './hooks/useUrlSync';
import { useDashboardStore } from './store/dashboard';

function Dashboard() {
  const initialize = useDashboardStore((s) => s.initialize);
  const mapStyle = useDashboardStore((s) => s.mapStyle);

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Sync assumptions → URL query params
  useUrlSync();

  // Sync CSS theme variables with the active map style
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mapStyle);
  }, [mapStyle]);

  return (
    <div className="h-screen relative bg-[#121212] overflow-hidden">
      {/* MAP — always full-screen. The bottom panel overlays it as a glass
          panel rather than pushing it. Resizing the map on toggle was expensive
          (MapLibre re-tiles) and visually awkward. Glass + blur makes the
          overlap feel intentional. */}
      <div data-tour="map" className="absolute inset-0">
        <MapView />
        <MapHint />
      </div>

      {/* HEADER + LEGEND STRIP — one absolute-positioned column so the
          strip naturally stacks below the Header at whatever height it
          happens to be. Previously the strip had a hardcoded `top: 62`
          that broke when typography changes grew the header. */}
      <div data-tour="header" className="absolute top-0 left-0 right-0 z-30 flex flex-col">
        <Header />
        <RasterLegend />
      </div>

      {/* ASSUMPTIONS PANEL */}
      <AssumptionsPanel />

      {/* SCORE DRAWER */}
      <ScoreDrawer />

      {/* BOTTOM PANEL */}
      <div data-tour="bottom-panel" className="absolute bottom-0 left-0 right-0 z-10">
        <BottomPanel />
      </div>

      {/* WALKTHROUGH TOUR */}
      <WalkthroughModal />
    </div>
  );
}

function App() {
  // Auth disabled 2026-05-07 — open access for now. Re-enable by restoring
  // the /api/auth/check fetch + LoginPage gate below, and uncommenting the
  // auth middleware in src/api/main.py + setting ACCESS_CODE on Render.
  // const [authed, setAuthed] = useState<boolean | null>(null);
  // useEffect(() => {
  //   fetch('/api/auth/check')
  //     .then((r) => r.json())
  //     .then((data) => setAuthed(data.authenticated))
  //     .catch(() => setAuthed(false));
  // }, []);
  // if (authed === null) {
  //   return <div className="h-screen w-screen bg-[#0a0a0c]" />;
  // }
  // if (!authed) {
  //   return <LoginPage onSuccess={() => setAuthed(true)} />;
  // }

  return <Dashboard />;
}

export default App;
