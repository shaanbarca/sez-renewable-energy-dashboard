import { useEffect } from 'react';
import { useDashboardStore } from './store/dashboard';
import Header from './components/ui/Header';
import MapView from './components/map/MapView';
import BottomPanel from './components/ui/BottomPanel';
import AssumptionsPanel from './components/panels/AssumptionsPanel';
import ScoreDrawer from './components/panels/ScoreDrawer';

function App() {
  const initialize = useDashboardStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="h-screen flex flex-col bg-[#121212]">
      <Header />
      <div className="flex-1 relative overflow-hidden">
        {/* MAP */}
        <MapView />

        {/* ASSUMPTIONS PANEL */}
        <AssumptionsPanel />

        {/* SCORE DRAWER */}
        <ScoreDrawer />

        {/* BOTTOM PANEL — inside map container so glass shows the map through */}
        <div className="absolute bottom-0 left-0 right-0 z-10">
          <BottomPanel />
        </div>
      </div>
    </div>
  );
}

export default App;
