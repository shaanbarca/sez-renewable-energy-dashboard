import { useEffect } from 'react';
import { useDashboardStore } from './store/dashboard';
import Header from './components/ui/Header';

function App() {
  const initialize = useDashboardStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="h-screen flex flex-col bg-[#121212]">
      <Header />
      <div className="flex-1 relative">
        {/* MAP slot - Lane C will fill this */}
        <div id="map-slot" className="absolute inset-0">
          <div className="flex items-center justify-center h-full text-zinc-600">
            Map placeholder
          </div>
        </div>

        {/* ASSUMPTIONS slot - Lane E will fill this */}

        {/* SCORE DRAWER slot - Lane E will fill this */}
      </div>

      {/* BOTTOM PANEL slot - Lane D will fill this */}
      <div id="bottom-slot" className="h-64 border-t border-white/10">
        <div className="flex items-center justify-center h-full text-zinc-600">
          Bottom panel placeholder
        </div>
      </div>
    </div>
  );
}

export default App;
