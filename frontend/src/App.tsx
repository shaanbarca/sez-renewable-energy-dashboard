import { useEffect, useRef, useState } from 'react';
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

  // The map's bottom inset is updated asymmetrically so MapLibre only
  // resizes once per toggle, not 18 times during a CSS transition:
  //   - Opening: wait for the panel's slide-up to finish, then shrink the map.
  //   - Closing: snap the map back to full-screen BEFORE the panel slides down
  //     (otherwise there'd be a visible gap at the bottom during the slide).
  //   - Drag-to-resize (splitMode stable, height changes): follow immediately.
  const [mapBottomInset, setMapBottomInset] = useState(0);
  const prevSplitModeRef = useRef(splitMode);
  useEffect(() => {
    const justToggled = prevSplitModeRef.current !== splitMode;
    prevSplitModeRef.current = splitMode;

    if (!splitMode) {
      setMapBottomInset(0);
      return;
    }
    if (justToggled) {
      const t = setTimeout(() => setMapBottomInset(bottomPanelHeight), 300);
      return () => clearTimeout(t);
    }
    // Stable split + height changed (drag). Follow continuously.
    setMapBottomInset(bottomPanelHeight);
  }, [splitMode, bottomPanelHeight]);

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
      {/* MAP — shrinks from the bottom in split mode, full-screen otherwise.
          No transition on purpose: animating this forces MapLibre to re-tile
          every frame, which is expensive with 81 markers + overlays. Snap. */}
      <div
        data-tour="map"
        className="absolute top-0 left-0 right-0"
        style={{ bottom: mapBottomInset }}
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
