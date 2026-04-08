import { useEffect } from 'react';
import { useDashboardStore } from './store/dashboard';
import Header from './components/ui/Header';
import MapView from './components/map/MapView';
import BottomPanel from './components/ui/BottomPanel';

function App() {
  const initialize = useDashboardStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="h-screen flex flex-col bg-[#121212]">
      <Header />
      <div className="flex-1 relative">
        {/* MAP - Lane C */}
        <MapView />

        {/* ASSUMPTIONS slot - Lane E will fill this */}

        {/* SCORE DRAWER slot - Lane E will fill this */}
      </div>

      {/* BOTTOM PANEL - Lane D */}
      <BottomPanel />
    </div>
  );
}

export default App;
