"use client";
import CameraPanel from '@components/CameraPanel';
import SettingsPopup from '@components/SettingsPopup';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { API_ENDPOINTS, WS_ENDPOINTS } from '@/lib/config';

export default function ViewsPage() {
  const router = useRouter();
  const [showSettings, setShowSettings] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(false);
  const [tempRange, setTempRange] = useState({ min: 0, max: 50 });
  const [colorPalette, setColorPalette] = useState('PLASMA');
  const [isBeachsideTheme, setIsBeachsideTheme] = useState(false);
  const [thermalControlsCollapsed, setThermalControlsCollapsed] = useState(false);

  // Apply beachside theme to body
  useEffect(() => {
    const body = document.getElementById('app-body');
    if (body) {
      if (isBeachsideTheme) {
        body.classList.add('beachside');
      } else {
        body.classList.remove('beachside');
      }
    }
  }, [isBeachsideTheme]);

  const wsBase = typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:8000`
    : 'ws://localhost:8000';

  // Navigation helper
  const navigateTo = (path: string) => {
    router.push(path);
  };

  // Keyboard shortcuts for thermal controls
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
      } else if (event.key === 'F1') {
        event.preventDefault();
        setShowSettings(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [filterEnabled, tempRange, colorPalette]);

  const toggleTemperatureFilter = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.THERMAL_FILTER_TOGGLE, {
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
      const response = await fetch(API_ENDPOINTS.THERMAL_FILTER_RANGE, {
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
      const response = await fetch(API_ENDPOINTS.THERMAL_PALETTE_CYCLE, {
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
      const response = await fetch(API_ENDPOINTS.THERMAL_CALIBRATE, {
        method: 'POST'
      });
      const data = await response.json();
      console.log('Manual calibration:', data.success ? 'SUCCESS' : 'FAILED');
    } catch (error) {
      console.error('Failed to calibrate:', error);
    }
  };

  return (
    <main className="min-h-screen relative">
      {/* Background Grid */}
      <div className="hud-grid absolute inset-0 opacity-30"></div>
      
      {/* Scanning Line */}
      <div className="scan-line"></div>
      
      {/* Top Command Bar */}
      <div className="tactical-panel m-2 p-3 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="status-indicator bg-success"></div>
            <h1 className="text-lg font-tactical font-semibold text-accent">
              Camera Views & Monitoring
            </h1>
            <div className="text-xs text-text-secondary font-mono">
              GOOD LUCK TEAM!!!
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Navigation Buttons */}
            <button
              onClick={() => navigateTo('/main')}
              className="tactical-button px-2 py-1 rounded text-xs"
              title="Main Dashboard"
            >
              MAIN
            </button>
            <button
              onClick={() => navigateTo('/controls')}
              className="tactical-button px-2 py-1 rounded text-xs"
              title="Robot Controls"
            >
              CONTROLS
            </button>
            <div className="text-xs text-text-secondary font-mono">
              {new Date().toISOString().slice(0, 19)}Z
            </div>
            <button 
              onClick={() => setIsBeachsideTheme(!isBeachsideTheme)}
              className={`tactical-button px-2 py-1 rounded text-xs ${isBeachsideTheme ? 'bg-beachside-medium hover:bg-beachside-light text-white' : ''}`}
              title="Toggle Beachside Theme"
            >
              {isBeachsideTheme ? 'BEACH' : 'OCEAN'}
            </button>
            <button
              onClick={() => setShowSettings(true)}
              className="tactical-button px-2 py-1 rounded text-xs"
              title="System Configuration"
            >
              CONFIG
            </button>
          </div>
        </div>
      </div>

      {/* Main Content - Full Screen Layout */}
      <div className="p-2">
        {/* Camera Feeds - Side by Side - Take up most of screen */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100vh-80px)] mb-6">
          {/* RGB Camera - Full Height */}
          <div className="bg-black rounded p-1 h-full">
            <CameraPanel title="RGB Camera" wsUrl={`${wsBase}/ws/rgb`} />
          </div>

          {/* Thermal Camera - Full Height */}
          <div className="bg-black rounded p-1 h-full">
            <CameraPanel 
              title="Thermal Camera" 
              wsUrl={`${wsBase}/ws/thermal`} 
              isThermal={true}
              filterEnabled={filterEnabled}
              tempRange={tempRange}
              colorPalette={colorPalette}
            />
          </div>
        </div>

        {/* Controls Section - Below Cameras */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pb-6">

          {/* System Status */}
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <div className="status-indicator bg-success"></div>
              <h3 className="text-sm font-tactical text-accent font-medium">System Status</h3>
            </div>
            <div className="grid grid-cols-1 gap-3 text-xs font-mono">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-text-secondary">CPU:</span>
                  <span className="text-success">23%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Memory:</span>
                  <span className="text-success">1.2GB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Network:</span>
                  <span className="text-success">ACTIVE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Uptime:</span>
                  <span className="text-text-primary">2h 14m</span>
                </div>
              </div>
            </div>
          </div>

          {/* Thermal Controls - Second Column */}
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="status-indicator bg-warning"></div>
                <h3 className="text-sm font-tactical text-accent font-medium">Thermal Controls</h3>
              </div>
              <button
                onClick={() => setThermalControlsCollapsed(!thermalControlsCollapsed)}
                className="tactical-button p-1 text-xs"
                title={thermalControlsCollapsed ? "Expand" : "Collapse"}
              >
                {thermalControlsCollapsed ? "▼" : "▲"}
              </button>
            </div>
            
            {!thermalControlsCollapsed && (
              <>
                {/* Temperature Filter Toggle */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-text-secondary">Temperature Filter</span>
                    <kbd className="px-1 py-0.5 text-xs bg-surface-dark border border-accent/30 rounded">Alt+F</kbd>
                  </div>
                  <Switch 
                    checked={filterEnabled}
                    onCheckedChange={(checked) => {
                      setFilterEnabled(checked);
                      toggleTemperatureFilter();
                    }}
                  />
                </div>

                  {/* Temperature Range Sliders */}
                  <div className="space-y-4 p-3 bg-surface-medium rounded border border-accent/20">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="text-xs text-accent font-mono font-bold">Min Temperature: {tempRange.min}°C</label>
                        <kbd className="px-1 py-0.5 text-xs bg-surface-dark border border-accent/30 rounded">Alt+T</kbd>
                      </div>
                      <div className="p-2 bg-surface-dark rounded">
                        <Slider
                          value={[tempRange.min]}
                          onValueChange={([value]) => {
                            // Ensure min doesn't exceed max
                            const clampedMin = Math.min(value, tempRange.max - 1);
                            const newRange = { ...tempRange, min: clampedMin };
                            setTempRange(newRange);
                            updateTemperatureRange(clampedMin, tempRange.max);
                          }}
                          max={99}
                          min={-20}
                          step={1}
                          className="w-full slider-enhanced"
                        />
                      </div>
                    </div>
                    <div className="space-y-3">
                      <label className="text-xs text-accent font-mono font-bold">Max Temperature: {tempRange.max}°C</label>
                      <div className="p-2 bg-surface-dark rounded">
                        <Slider
                          value={[tempRange.max]}
                          onValueChange={([value]) => {
                            // Ensure max doesn't go below min
                            const clampedMax = Math.max(value, tempRange.min + 1);
                            const newRange = { ...tempRange, max: clampedMax };
                            setTempRange(newRange);
                            updateTemperatureRange(tempRange.min, clampedMax);
                          }}
                          max={100}
                          min={-19}
                          step={1}
                          className="w-full slider-enhanced"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Color Palette */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-secondary">Color Palette</span>
                      <kbd className="px-1 py-0.5 text-xs bg-surface-dark border border-accent/30 rounded">Alt+P</kbd>
                    </div>
                    <button 
                      onClick={cycleColorPalette}
                      className="tactical-button px-3 py-1 rounded text-xs"
                    >
                      {colorPalette}
                    </button>
                  </div>

                  {/* Manual Calibration */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-secondary">Manual Calibration</span>
                      <kbd className="px-1 py-0.5 text-xs bg-surface-dark border border-accent/30 rounded">Alt+C</kbd>
                    </div>
                    <button 
                      onClick={manualCalibration}
                      className="tactical-button px-3 py-1 rounded text-xs"
                    >
                      CALIBRATE
                    </button>
                  </div>

                  {/* Settings Access */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-secondary">Settings Panel</span>
                      <kbd className="px-1 py-0.5 text-xs bg-surface-dark border border-accent/30 rounded">F1</kbd>
                    </div>
                    <button 
                      onClick={() => setShowSettings(true)}
                      className="tactical-button px-3 py-1 rounded text-xs"
                    >
                      CONFIG
                    </button>
                  </div>
              </>
            )}
          </div>
        </div>
      </div>

      <SettingsPopup 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)} 
      />
    </main>
  );
}