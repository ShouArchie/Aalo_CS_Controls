"use client";
import CameraPanel from '@components/CameraPanel';
import SettingsPopup from '@components/SettingsPopup';
import JointConfigPopup from '@components/JointConfigPopup';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function MainDashboard() {
  const router = useRouter();
  const [showSettings, setShowSettings] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(false);
  const [tempRange, setTempRange] = useState({ min: 0, max: 50 });
  const [colorPalette, setColorPalette] = useState('PLASMA');
  
  // Robot control states
  const [robotIp, setRobotIp] = useState('192.168.10.255');
  const [robotConnected, setRobotConnected] = useState(false);
  const [robotStatus, setRobotStatus] = useState('DISCONNECTED');
  const [robotPosition, setRobotPosition] = useState('UNKNOWN');
  const [thermalTracking, setThermalTracking] = useState(false);
  
  // Home joint configuration (in degrees)
  const [homeJoints, setHomeJoints] = useState([206.06, -66.96, 104.35, 232.93, 269.26, 118.75]);
  const [showJointConfig, setShowJointConfig] = useState(false);
  
  // Fine movement configuration
  const [fineStepSize, setFineStepSize] = useState(1.0);  // mm
  const [fineVelocity, setFineVelocity] = useState(0.1);  // m/s
  const [fineAcceleration, setFineAcceleration] = useState(0.1);  // m/s²
  const [rotationAngle, setRotationAngle] = useState(5.0);  // degrees
  
  // TCP configuration
  const [selectedTcp, setSelectedTcp] = useState(1);
  const [customTcp, setCustomTcp] = useState([0, 0, 0, 0, 0, 0]); // [x, y, z, rx, ry, rz]
  
  // Global speed control
  const [globalSpeedPercent, setGlobalSpeedPercent] = useState(100);  // 0-100%
  const [baseSpeed, setBaseSpeed] = useState(0.1);  // Base speed for speedL (m/s)
  
  // Theme control
  const [isBeachsideTheme, setIsBeachsideTheme] = useState(false);
  
  // Thermal controls collapse state
  const [thermalControlsCollapsed, setThermalControlsCollapsed] = useState(false);

  // TCP Presets
  const TCP_PRESETS: Record<number, { name: string; offset: number[] }> = {
    1: { name: "Primary TCP", offset: [-278.81, 0.0, 60.3, 0.0, 0.0, 0.0] },
    2: { name: "Secondary TCP (Temporary)", offset: [-278.81, 0.0, 60.3, 0.0, 0.0, 0.0] },
    3: { name: "Tertiary TCP (Temporary)", offset: [-278.81, 0.0, 60.3, 0.0, 0.0, 0.0] },
    4: { name: "No TCP (Base)", offset: [0, 0, 0, 0, 0, 0] },
    5: { name: "Custom TCP", offset: customTcp }
  };

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

  // Apply selected TCP when robot connects
  useEffect(() => {
    if (robotConnected && selectedTcp) {
      console.log(`🤖 Robot connected - applying saved TCP ${selectedTcp}`);
      setTcp(selectedTcp);
    }
  }, [robotConnected]);

  const wsBase = typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:8000`
    : 'ws://localhost:8000';

  // Navigation helper
  const navigateTo = (path: string) => {
    router.push(path);
  };

  // Thermal control functions
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

  // Robot control functions
  const connectRobot = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip: robotIp })
      });
      if (response.ok) {
        const data = await response.json();
        setRobotConnected(data.connected);
        setRobotStatus(data.connected ? 'CONNECTED' : 'FAILED');
        console.log('Robot connection:', data);
      }
    } catch (error) {
      console.error('Failed to connect robot:', error);
      setRobotStatus('ERROR');
    }
  };

  const disconnectRobot = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/disconnect', {
        method: 'POST'
      });
      if (response.ok) {
        setRobotConnected(false);
        setRobotStatus('DISCONNECTED');
        setThermalTracking(false);
      }
    } catch (error) {
      console.error('Failed to disconnect robot:', error);
    }
  };

  const setTcp = async (tcpId: number) => {
    try {
      if (!robotConnected) {
        console.log(`⚠️ Robot not connected - TCP ${tcpId} selection saved but not applied`);
        setSelectedTcp(tcpId);
        return;
      }

      const tcpOffset = tcpId === 5 ? customTcp : TCP_PRESETS[tcpId].offset;
      console.log(`🔧 Applying TCP ${tcpId} to robot: [${tcpOffset.join(', ')}]`);
      
      const response = await fetch('http://localhost:8000/api/robot/set-tcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          tcp_offset: tcpOffset,
          tcp_id: tcpId,
          tcp_name: TCP_PRESETS[tcpId].name
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setSelectedTcp(tcpId);
        console.log(`✅ TCP ${tcpId} applied to robot successfully:`, result.message);
      } else {
        const error = await response.json();
        console.error('Failed to set TCP:', error.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to set TCP:', error);
    }
  };

  return (
    <main className="min-h-screen relative overflow-hidden">
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
              UR-10E Control Dashboard
            </h1>
            <div className="text-xs text-text-secondary font-mono">
              SYS.ONLINE | AUTH.GRANTED
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Navigation Buttons */}
            <button
              onClick={() => navigateTo('/views')}
              className="tactical-button px-2 py-1 rounded text-xs"
              title="Camera Views"
            >
              VIEWS
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

      {/* Main Content Grid */}
      <div className="p-2 h-[calc(100vh-80px)]">
        <div className="grid grid-cols-1 lg:grid-cols-6 gap-4 h-full">
          {/* Camera Feeds - Left Side */}
          <div className="lg:col-span-2 space-y-3">
            {/* RGB Camera */}
            <div className="bg-black rounded p-3">
              <CameraPanel title="RGB Camera" wsUrl={`${wsBase}/ws/rgb`} />
            </div>

            {/* Thermal Camera */}
            <div className="bg-black rounded p-3">
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

          {/* Control Panels - Right Side (4 columns) */}
          <div className="lg:col-span-4 space-y-3 h-full">
            {/* System Status */}
            <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-3">
              <div className="flex items-center gap-2">
                <div className="status-indicator bg-success"></div>
                <h3 className="text-sm font-tactical text-accent font-medium">System Status</h3>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">CPU:</span>
                    <span className="text-success">23%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Memory:</span>
                    <span className="text-success">1.2GB</span>
                  </div>
                </div>
                <div className="space-y-1">
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

            {/* Basic Thermal Controls */}
            <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-4 flex-1">
              <div className="flex items-center gap-2">
                <div className="status-indicator bg-warning"></div>
                <h3 className="text-sm font-tactical text-accent font-medium">Thermal Controls</h3>
              </div>
              
              {/* Temperature Filter Toggle */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Temperature Filter</span>
                <Switch 
                  checked={filterEnabled}
                  onCheckedChange={(checked) => {
                    setFilterEnabled(checked);
                    toggleTemperatureFilter();
                  }}
                />
              </div>

              {/* Color Palette */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">Color Palette</span>
                <button 
                  onClick={cycleColorPalette}
                  className="tactical-button px-3 py-1 rounded text-xs"
                >
                  {colorPalette}
                </button>
              </div>
            </div>

            {/* Basic Robot Controls */}
            <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-4">
              <div className="flex items-center gap-2">
                <div className={`status-indicator ${robotConnected ? 'bg-success' : 'bg-warning'}`}></div>
                <h3 className="text-sm font-tactical text-accent font-medium">UR10e Robot Control</h3>
              </div>
              
              {/* Robot IP Configuration */}
              <div className="space-y-2">
                <label className="text-xs text-text-secondary">Robot IP Address</label>
                <div className="flex gap-2">
                  <Input
                    value={robotIp}
                    onChange={(e) => setRobotIp(e.target.value)}
                    placeholder="192.168.10.255"
                    className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                  />
                  <button 
                    onClick={robotConnected ? disconnectRobot : connectRobot}
                    className={`tactical-button px-3 py-1 rounded text-xs ${robotConnected ? 'bg-danger hover:bg-danger/80' : ''}`}
                  >
                    {robotConnected ? 'DISCONNECT' : 'CONNECT'}
                  </button>
                </div>
              </div>

              {/* Robot Status */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Status:</span>
                    <span className={robotConnected ? 'text-success' : 'text-warning'}>{robotStatus}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Position:</span>
                    <span className="text-text-primary">{robotPosition}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Mode:</span>
                    <span className="text-text-primary">MANUAL</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <SettingsPopup 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)} 
      />

      <JointConfigPopup
        isOpen={showJointConfig}
        onClose={() => setShowJointConfig(false)}
        homeJoints={homeJoints}
        onUpdate={setHomeJoints}
        onSave={() => {}}
      />
    </main>
  );
}