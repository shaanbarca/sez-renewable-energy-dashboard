import { useEffect } from 'react';
import MapView from './components/map/MapView';
import RasterLegend from './components/map/RasterLegend';
import AssumptionsPanel from './components/panels/AssumptionsPanel';
import ScoreDrawer from './components/panels/ScoreDrawer';
import BottomPanel from './components/ui/BottomPanel';
import Header from './components/ui/Header';
import WalkthroughModal from './components/ui/WalkthroughModal';
import { useDashboardStore } from './store/dashboard';

function App() {
  const initialize = useDashboardStore((s) => s.initialize);
  const mapStyle = useDashboardStore((s) => s.mapStyle);

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Sync CSS theme variables with the active map style
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', mapStyle);
  }, [mapStyle]);

  return (
    <div className="h-screen relative bg-[#121212] overflow-hidden">
      {/* MAP — full screen behind everything */}
      <div data-tour="map" className="absolute inset-0">
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

export default App;
