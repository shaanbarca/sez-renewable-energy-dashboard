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
        {/* MAP - Lane C */}
        <MapView />

        {/* ASSUMPTIONS PANEL - Lane E */}
        <AssumptionsPanel />

        {/* SCORE DRAWER - Lane E */}
        <ScoreDrawer />
      </div>

      {/* BOTTOM PANEL - Lane D */}
      <BottomPanel />
    </div>
  );
}

export default App;
