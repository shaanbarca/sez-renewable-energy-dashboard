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
      </div>

      {/* BOTTOM PANEL */}
      <BottomPanel />
    </div>
  );
}

export default App;
