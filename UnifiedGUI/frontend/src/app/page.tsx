"use client";
import CameraPanel from '@components/CameraPanel';
import SettingsPopup from '@components/SettingsPopup';
import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [showSettings, setShowSettings] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(false);
  const [tempRange, setTempRange] = useState({ min: 0, max: 50 });
  const [colorPalette, setColorPalette] = useState('PLASMA');

  const wsBase = typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:8000`
    : 'ws://localhost:8000';

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.altKey) {
        switch (event.key.toLowerCase()) {
          case 'f':
            event.preventDefault();
            toggleTemperatureFilter();
            break;
          case 't':
            event.preventDefault();
            adjustTemperatureRange();
            break;
          case 'p':
            event.preventDefault();
            cycleColorPalette();
            break;
          case 'c':
            event.preventDefault();
            manualCalibration();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filterEnabled, tempRange, colorPalette]);

  const toggleTemperatureFilter = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/thermal/filter/toggle', {
        method: 'POST'
      });
      const data = await response.json();
      setFilterEnabled(data.enabled);
      console.log(`Temperature filter ${data.enabled ? 'ENABLED' : 'DISABLED'}`);
    } catch (error) {
      console.error('Failed to toggle filter:', error);
    }
  };

  const adjustTemperatureRange = () => {
    const min = prompt(`Enter minimum temperature (°C):`, tempRange.min.toString());
    const max = prompt(`Enter maximum temperature (°C):`, tempRange.max.toString());
    
    if (min !== null && max !== null) {
      const minVal = parseFloat(min);
      const maxVal = parseFloat(max);
      
      if (!isNaN(minVal) && !isNaN(maxVal) && minVal < maxVal) {
        updateTemperatureRange(minVal, maxVal);
      } else {
        alert('Invalid temperature range. Min must be less than max.');
      }
    }
  };

  const updateTemperatureRange = async (min: number, max: number) => {
    try {
      const response = await fetch('http://localhost:8000/api/thermal/filter/range', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ min_temp: min, max_temp: max })
      });
      const data = await response.json();
      if (data.success) {
        setTempRange({ min, max });
        console.log(`Temperature range updated: ${min}°C to ${max}°C`);
      }
    } catch (error) {
      console.error('Failed to update temperature range:', error);
    }
  };

  const cycleColorPalette = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/thermal/palette/cycle', {
        method: 'POST'
      });
      const data = await response.json();
      setColorPalette(data.palette);
      console.log(`Switched to ${data.palette} color palette`);
    } catch (error) {
      console.error('Failed to cycle color palette:', error);
    }
  };

  const manualCalibration = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/thermal/calibrate', {
        method: 'POST'
      });
      const data = await response.json();
      console.log('Manual calibration:', data.success ? 'SUCCESS' : 'FAILED');
    } catch (error) {
      console.error('Failed to calibrate:', error);
    }
  };

  return (
    <main className="min-h-screen p-6 flex flex-col items-center gap-6 relative">
      <div className="flex items-center justify-between w-full max-w-5xl">
        <h1 className="text-3xl font-bold text-accent drop-shadow-glow">UR 10e Control Dashboard</h1>
        <button
          onClick={() => setShowSettings(true)}
          className="bg-gray-800 hover:bg-gray-700 text-white p-2 rounded-lg transition-colors"
          title="Settings & Shortcuts"
        >
          ⚙️
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-5xl">
        <CameraPanel title="RGB Camera" wsUrl={`${wsBase}/ws/rgb`} />
        <CameraPanel 
          title="Thermal Camera" 
          wsUrl={`${wsBase}/ws/thermal`} 
          isThermal={true}
          filterEnabled={filterEnabled}
          tempRange={tempRange}
          colorPalette={colorPalette}
        />
      </div>

      <SettingsPopup 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)} 
      />
    </main>
  );
} 