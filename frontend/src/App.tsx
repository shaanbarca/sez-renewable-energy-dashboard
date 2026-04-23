import { useEffect, useState } from 'react';
import MapView from './components/map/MapView';
import RasterLegend from './components/map/RasterLegend';
import AssumptionsPanel from './components/panels/AssumptionsPanel';
import ScoreDrawer from './components/panels/ScoreDrawer';
import BottomPanel from './components/ui/BottomPanel';
import Header from './components/ui/Header';
import LoginPage from './components/ui/LoginPage';
import WalkthroughModal from './components/ui/WalkthroughModal';
import { useUrlSync } from './hooks/useUrlSync';
import { useDashboardStore } from './store/dashboard';

function Dashboard() {
  const initialize = useDashboardStore((s) => s.initialize);
  const mapStyle = useDashboardStore((s) => s.mapStyle);
  const activeTab = useDashboardStore((s) => s.activeTab);
  const bottomPanelCollapsed = useDashboardStore((s) => s.bottomPanelCollapsed);
  const bottomPanelHeight = useDashboardStore((s) => s.bottomPanelHeight);

  // Split mode: Ranked Table paired with map so both are visible.
  // Other tabs (charts / Scenario Compare) keep overlay behavior.
  const splitMode = activeTab === 'table' && !bottomPanelCollapsed;
  const mapBottomInset = splitMode ? bottomPanelHeight : 0;

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
      {/* MAP — shrinks from the bottom in split mode, full-screen otherwise */}
      <div
        data-tour="map"
        className="absolute top-0 left-0 right-0"
        style={{
          bottom: mapBottomInset,
          transition: 'bottom 0.3s ease-in-out',
        }}
      >
        <MapView />
      </div>

      {/* HEADER — liquid glass overlay on top of map */}
      <div data-tour="header" className="absolute top-0 left-0 right-0 z-30">
        <Header />
      </div>

      {/* ASSUMPTIONS PANEL */}
      <AssumptionsPanel />

      {/* SCORE DRAWER */}
      <ScoreDrawer />

      {/* RASTER LEGENDS */}
      <RasterLegend />

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
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    fetch('/api/auth/check')
      .then((r) => r.json())
      .then((data) => setAuthed(data.authenticated))
      .catch(() => setAuthed(false));
  }, []);

  if (authed === null) {
    return <div className="h-screen w-screen bg-[#0a0a0c]" />;
  }

  if (!authed) {
    return <LoginPage onSuccess={() => setAuthed(true)} />;
  }

  return <Dashboard />;
}

export default App;
