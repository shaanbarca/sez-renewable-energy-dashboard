import { useEffect } from 'react';
import { useDashboardStore } from './store/dashboard';
import Header from './components/ui/Header';
import MapView from './components/map/MapView';
import BottomPanel from './components/ui/BottomPanel';
import AssumptionsPanel from './components/panels/AssumptionsPanel';
import ScoreDrawer from './components/panels/ScoreDrawer';
import RasterLegend from './components/map/RasterLegend';

function App() {
  const initialize = useDashboardStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="h-screen relative bg-[#121212] overflow-hidden">
      {/* MAP — full screen behind everything */}
      <MapView />

      {/* HEADER — liquid glass overlay on top of map */}
      <div className="absolute top-0 left-0 right-0 z-30">
        <Header />
      </div>

      {/* ASSUMPTIONS PANEL */}
      <AssumptionsPanel />

      {/* SCORE DRAWER */}
      <ScoreDrawer />

      {/* RASTER LEGENDS */}
      <RasterLegend />

      {/* BOTTOM PANEL */}
      <div className="absolute bottom-0 left-0 right-0 z-10">
        <BottomPanel />
      </div>
    </div>
  );
}

export default App;
