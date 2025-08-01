"use client";
import CameraPanel from '@components/CameraPanel';
import SettingsPopup from '@components/SettingsPopup';
import JointConfigPopup from '@components/JointConfigPopup';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect } from 'react';

export default function Dashboard() {
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
  const TCP_PRESETS = {
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
      } else if (event.key === 'F1') {
        event.preventDefault();
        setShowSettings(true);
      }
      // WASD robot movement (only when robot is connected and not typing in input)
      else if (robotConnected && document.activeElement?.tagName !== 'INPUT') {
        switch (event.key.toLowerCase()) {
          case 'w':
            event.preventDefault();
            moveRobot('z+');
            break;
          case 's':
            event.preventDefault();
            moveRobot('z-');
            break;
          case 'a':
            event.preventDefault();
            moveRobot('y-');
            break;
          case 'd':
            event.preventDefault();
            moveRobot('y+');
            break;
          case 'q':
            event.preventDefault();
            moveRobot('x+');
            break;
          case 'e':
            event.preventDefault();
            moveRobot('x-');
            break;
          // IJKL for fine movements (use UI step size)
          case 'i':
            event.preventDefault();
            moveFine('z+', fineStepSize);
            break;
          case 'k':
            event.preventDefault();
            moveFine('z-', fineStepSize);
            break;
          case 'j':
            event.preventDefault();
            moveFine('y-', fineStepSize);
            break;
          case 'l':
            event.preventDefault();
            moveFine('y+', fineStepSize);
            break;
          case 'u':
            event.preventDefault();
            moveFine('x+', fineStepSize);
            break;
          case 'o':
            event.preventDefault();
            moveFine('x-', fineStepSize);
            break;
          // R/F for Rx rotation (fine movements)
          case 'r':
            event.preventDefault();
            moveRotation('rx+', rotationAngle);
            break;
          case 'f':
            event.preventDefault();
            moveRotation('rx-', rotationAngle);
            break;
          // T/G for Ry rotation (fine movements)
          case 't':
            event.preventDefault();
            moveRotation('ry+', rotationAngle);
            break;
          case 'g':
            event.preventDefault();
            moveRotation('ry-', rotationAngle);
            break;
          // Y/H for Rz rotation (fine movements)
          case 'y':
            event.preventDefault();
            moveRotation('rz+', rotationAngle);
            break;
          case 'h':
            event.preventDefault();
            moveRotation('rz-', rotationAngle);
            break;
        }
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      // Stop robot movement on key release for WASD
      if (robotConnected && document.activeElement?.tagName !== 'INPUT') {
        switch (event.key.toLowerCase()) {
          case 'w':
          case 's':
          case 'a':
          case 'd':
          case 'q':
          case 'e':
            event.preventDefault();
            stopRobot();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [filterEnabled, tempRange, colorPalette, robotConnected, fineStepSize, globalSpeedPercent, baseSpeed, rotationAngle]);

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

  const moveToHome = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/home', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed_percent: globalSpeedPercent })
      });
      if (response.ok) {
        setRobotPosition('HOME');
      }
    } catch (error) {
      console.error('Failed to move to home:', error);
    }
  };

  const moveToHomeJoints = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/home-joints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          joints: homeJoints,
          speed_percent: globalSpeedPercent 
        })
      });
      if (response.ok) {
        setRobotPosition('HOME_JOINTS');
      }
    } catch (error) {
      console.error('Failed to move to home joints:', error);
    }
  };

  const updateHomeJoints = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/config/home-joints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ joints: homeJoints })
      });
      if (response.ok) {
        console.log('Home joints configuration updated');
        setShowJointConfig(false);
      }
    } catch (error) {
      console.error('Failed to update home joints config:', error);
    }
  };

  const toggleThermalTracking = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/thermal-tracking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !thermalTracking })
      });
      if (response.ok) {
        setThermalTracking(!thermalTracking);
      }
    } catch (error) {
      console.error('Failed to toggle thermal tracking:', error);
    }
  };

  const moveRobot = async (direction: string, distance: number = 0.05) => {
    try {
      console.log(`🚀 Frontend moveRobot: direction=${direction}, speed_percent=${globalSpeedPercent}%, base_speed=${baseSpeed}`);
      const response = await fetch('http://localhost:8000/api/robot/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          direction, 
          distance,
          speed_percent: globalSpeedPercent,
          base_speed: baseSpeed
        })
      });
      if (!response.ok) {
        console.error('Failed to move robot');
      }
    } catch (error) {
      console.error('Failed to move robot:', error);
    }
  };

  const stopRobot = async () => {
    try {
      console.log('🛑 Frontend stopRobot called - sending immediate stop');
      
      // Send stop command without waiting for response to minimize delay
      fetch('http://localhost:8000/api/robot/stop', {
        method: 'POST'
      }).catch(error => {
        console.error('Failed to stop robot:', error);
      });
      
      // Also send a second stop command with a tiny delay for redundancy
      setTimeout(() => {
        fetch('http://localhost:8000/api/robot/stop', {
          method: 'POST'
        }).catch(error => {
          console.error('Failed to send redundant stop:', error);
        });
      }, 10); // 10ms delay
      
    } catch (error) {
      console.error('Failed to stop robot:', error);
    }
  };

  const moveFine = async (direction: string, stepSize: number = fineStepSize) => {
    try {
      // Apply global speed multiplier to velocity and acceleration
      const adjustedVelocity = fineVelocity * (globalSpeedPercent / 100);
      const adjustedAcceleration = fineAcceleration * (globalSpeedPercent / 100);
      
      const response = await fetch('http://localhost:8000/api/robot/move-fine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          direction, 
          step_size_mm: stepSize,
          velocity: adjustedVelocity,
          acceleration: adjustedAcceleration
        })
      });
      if (!response.ok) {
        console.error('Failed to move robot fine');
      }
    } catch (error) {
      console.error('Failed to move robot fine:', error);
    }
  };

  const moveRotation = async (axis: string, angle: number = rotationAngle) => {
    try {
      console.log(`🔄 Frontend moveRotation: axis=${axis}, angle=${angle}°, speed_percent=${globalSpeedPercent}%`);
      
      // Apply global speed multiplier to angular velocity
      const adjustedAngularVelocity = 0.1 * (globalSpeedPercent / 100); // Base angular velocity in rad/s
      
      const response = await fetch('http://localhost:8000/api/robot/move-rotation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          axis, 
          angle_deg: angle,
          angular_velocity: adjustedAngularVelocity,
          speed_percent: globalSpeedPercent
        })
      });
      if (!response.ok) {
        console.error('Failed to move robot rotation');
      }
    } catch (error) {
      console.error('Failed to move robot rotation:', error);
    }
  };

  const updateFineStepSize = async (newStepSize: number) => {
    try {
      const response = await fetch('http://localhost:8000/api/robot/config/step-size', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_size_mm: newStepSize })
      });
      if (response.ok) {
        setFineStepSize(newStepSize);
        console.log(`Fine step size updated to ${newStepSize}mm`);
      }
    } catch (error) {
      console.error('Failed to update step size:', error);
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
          <div className="lg:col-span-2 space-y-3 relative">
            {/* 3D Background Effect */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-10">
              <div className="robotic-hand-container">
                <svg className="robotic-hand-svg" viewBox="0 0 400 400" style={{width: '100%', height: '100%'}}>
                  {/* Robotic Hand Outline */}
                  <g className="animate-spin-slow">
                    {/* Palm */}
                    <path d="M150 200 L150 160 L190 140 L230 140 L270 160 L270 200 L270 240 L230 260 L190 260 L150 240 Z" 
                          fill="none" stroke="#FFA200" strokeWidth="2" opacity="0.6"/>
                    
                    {/* Fingers */}
                    <g stroke="#FFA200" strokeWidth="1.5" fill="none" opacity="0.4">
                      {/* Thumb */}
                      <path d="M150 180 L120 170 L110 150 L115 130 L130 125 L145 135"/>
                      
                      {/* Index finger */}
                      <path d="M170 140 L165 110 L170 90 L180 85 L190 90 L185 110"/>
                      
                      {/* Middle finger */}
                      <path d="M200 140 L200 105 L205 80 L215 75 L225 80 L220 105"/>
                      
                      {/* Ring finger */}
                      <path d="M230 140 L235 110 L240 90 L250 85 L260 90 L255 110"/>
                      
                      {/* Pinky */}
                      <path d="M250 140 L255 115 L260 100 L270 95 L280 100 L275 115"/>
                    </g>
                    
                    {/* Joints */}
                    <g fill="#FFA200" opacity="0.7">
                      <circle cx="170" cy="140" r="3"/>
                      <circle cx="200" cy="140" r="3"/>
                      <circle cx="230" cy="140" r="3"/>
                      <circle cx="250" cy="140" r="3"/>
                      <circle cx="150" cy="180" r="3"/>
                    </g>
                    
                    {/* Wrist joint */}
                    <circle cx="210" cy="260" r="8" fill="none" stroke="#FFA200" strokeWidth="2" opacity="0.6"/>
                    <path d="M200 270 L220 270 M210 260 L210 280" stroke="#FFA200" strokeWidth="1" opacity="0.4"/>
                  </g>
                  
                  {/* Additional tech elements */}
                  <g opacity="0.3">
                    <circle cx="350" cy="100" r="30" fill="none" stroke="#00D9FF" strokeWidth="1" className="animate-pulse"/>
                    <circle cx="50" cy="350" r="20" fill="none" stroke="#FF6B35" strokeWidth="1" className="animate-pulse"/>
                    <path d="M300 350 L350 350 M325 330 L325 370" stroke="#FFA200" strokeWidth="1" opacity="0.5"/>
                  </g>
                </svg>
              </div>
            </div>

            {/* RGB Camera */}
            <div className="bg-black rounded p-3 relative z-10">
              <CameraPanel title="RGB Camera" wsUrl={`${wsBase}/ws/rgb`} />
            </div>

            {/* Thermal Camera */}
            <div className="bg-black rounded p-3 relative z-10">
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
            {/* System Status - Dynamic Section */}
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

            {/* Thermal Controls - Dynamic Section */}
            <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-4 flex-1 overflow-y-auto">
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
                        const newRange = { ...tempRange, min: value };
                        setTempRange(newRange);
                        updateTemperatureRange(value, tempRange.max);
                      }}
                      max={tempRange.max - 1}
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
                        const newRange = { ...tempRange, max: value };
                        setTempRange(newRange);
                        updateTemperatureRange(tempRange.min, value);
                      }}
                      max={100}
                      min={tempRange.min + 1}
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

            {/* Robot Controls - Dynamic Section */}
            <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-4">
              <div className="flex items-center gap-2">
                <div className={`status-indicator ${robotConnected ? 'bg-success' : 'bg-warning'}`}></div>
                <h3 className="text-sm font-tactical text-accent font-medium">UR10e Robot Control</h3>
              </div>

              {/* TCP Configuration */}
              <div className="space-y-2 border-b border-accent/20 pb-3">
                <label className="text-xs text-accent font-tactical">TCP Configuration</label>
                <div className="space-y-2">
                  <Select 
                    value={selectedTcp.toString()} 
                    onValueChange={(value) => {
                      const tcpId = parseInt(value);
                      setTcp(tcpId);
                    }}
                  >
                    <SelectTrigger className="text-xs bg-surface-dark border-accent/30 text-text-primary">
                      <SelectValue placeholder="Select TCP" />
                    </SelectTrigger>
                    <SelectContent className="bg-surface-dark border-accent/30">
                      <SelectItem value="1" className="text-xs text-text-primary hover:bg-accent/20">
                        1: Primary TCP (-278.81, 0, 60.3)
                      </SelectItem>
                      <SelectItem value="2" className="text-xs text-text-primary hover:bg-accent/20">
                        2: Secondary TCP (Temporary)
                      </SelectItem>
                      <SelectItem value="3" className="text-xs text-text-primary hover:bg-accent/20">
                        3: Tertiary TCP (Temporary)
                      </SelectItem>
                      <SelectItem value="4" className="text-xs text-text-primary hover:bg-accent/20">
                        4: No TCP (Base Coordinates)
                      </SelectItem>
                      <SelectItem value="5" className="text-xs text-text-primary hover:bg-accent/20">
                        5: Custom TCP
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  
                  {/* Custom TCP Input (when option 5 selected) */}
                  {selectedTcp === 5 && (
                    <div className="space-y-2">
                      <label className="text-xs text-text-secondary">Custom TCP Offset (X, Y, Z, Rx, Ry, Rz)</label>
                      <div className="grid grid-cols-6 gap-1">
                        {customTcp.map((value, index) => (
                          <Input
                            key={index}
                            type="number"
                            value={value}
                            onChange={(e) => {
                              const newTcp = [...customTcp];
                              newTcp[index] = parseFloat(e.target.value) || 0;
                              setCustomTcp(newTcp);
                            }}
                            placeholder={['X', 'Y', 'Z', 'Rx', 'Ry', 'Rz'][index]}
                            className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                            step={index < 3 ? "0.1" : "0.01"}
                          />
                        ))}
                      </div>
                      <button 
                        onClick={() => setTcp(5)}
                        className="tactical-button py-1 px-3 rounded text-xs w-full"
                      >
                        Apply Custom TCP
                      </button>
                    </div>
                  )}
                </div>
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
                    <span className="text-text-secondary">Thermal Track:</span>
                    <span className={thermalTracking ? 'text-success' : 'text-text-secondary'}>
                      {thermalTracking ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Mode:</span>
                    <span className="text-text-primary">MANUAL</span>
                  </div>
                </div>
              </div>

              {/* Robot Controls */}
              {robotConnected && (
                <div className="space-y-3">
                  {/* Tracking Controls */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-secondary">Thermal Tracking</span>
                    <Switch 
                      checked={thermalTracking}
                      onCheckedChange={toggleThermalTracking}
                    />
                  </div>

                  {/* Speed Controls */}
                  <div className="space-y-3 border-b border-accent/20 pb-3">
                    <h4 className="text-xs text-accent font-tactical">Speed Configuration</h4>
                    
                    {/* Base Speed Input */}
                    <div className="space-y-1">
                      <label className="text-xs text-text-secondary">Base Speed (m/s)</label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          value={baseSpeed}
                          onChange={(e) => {
                            const inputValue = e.target.value;
                            if (inputValue === '' || inputValue === '0') {
                              setBaseSpeed(0.01); // Minimum value when cleared
                            } else {
                              const value = parseFloat(inputValue);
                              if (!isNaN(value) && value > 0) {
                                setBaseSpeed(Math.min(Math.max(value, 0.0001), 1.0)); // Clamp between 0.01 and 1.0
                              }
                            }
                          }}
                          step="0.01"
                          min="0.01"
                          max="1.0"
                          className="text-xs bg-surface-dark border-accent/30 text-text-primary flex-1"
                        />
                        <div className="flex gap-1">
                          <button onClick={() => setBaseSpeed(0.05)} className="tactical-button py-1 px-2 text-xs">0.05</button>
                          <button onClick={() => setBaseSpeed(0.1)} className="tactical-button py-1 px-2 text-xs">0.1</button>
                          <button onClick={() => setBaseSpeed(0.2)} className="tactical-button py-1 px-2 text-xs">0.2</button>
                        </div>
                      </div>
                    </div>

                    {/* Compact Global Speed Control */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-text-secondary">Global Speed</span>
                        <span className="text-accent font-bold">{globalSpeedPercent}%</span>
                      </div>
                      <div className="flex gap-2 items-center">
                        <div className="slider-enhanced flex-1">
                          <Slider
                            value={[globalSpeedPercent]}
                            onValueChange={(value) => setGlobalSpeedPercent(value[0])}
                            min={0}
                            max={100}
                            step={5}
                            className="w-full"
                          />
                        </div>
                        <div className="flex gap-1">
                          <button onClick={() => setGlobalSpeedPercent(50)} className="tactical-button py-1 px-1 text-xs">50%</button>
                          <button onClick={() => setGlobalSpeedPercent(100)} className="tactical-button py-1 px-1 text-xs">100%</button>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Continuous Movement Controls */}
                  <div className="space-y-2">
                    <h4 className="text-xs text-accent font-tactical">Continuous Movement (Base Coordinates)</h4>
                    <div className="grid grid-cols-3 gap-1">
                      {/* Translation Controls - Hold to move continuously */}
                      <button 
                        onMouseDown={() => moveRobot('x+')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        +X
                      </button>
                      <button 
                        onMouseDown={() => moveRobot('y+')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        +Y
                      </button>
                      <button 
                        onMouseDown={() => moveRobot('z+')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        +Z
                      </button>
                      <button 
                        onMouseDown={() => moveRobot('x-')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        -X
                      </button>
                      <button 
                        onMouseDown={() => moveRobot('y-')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        -Y
                      </button>
                      <button 
                        onMouseDown={() => moveRobot('z-')} 
                        onMouseUp={stopRobot}
                        onMouseLeave={stopRobot}
                        className="tactical-button py-1 px-2 text-xs select-none"
                      >
                        -Z
                      </button>
                    </div>
                    
                    {/* Large Emergency Stop Button */}
                    <div className="flex justify-center">
                      <button 
                        onClick={stopRobot}
                        className="w-20 h-20 bg-red-600 hover:bg-red-700 text-white font-bold text-sm border-2 border-red-500 shadow-lg hover:shadow-red-500/50 transition-all duration-200 flex flex-col items-center justify-center gap-1 active:scale-95"
                        style={{
                          background: 'linear-gradient(145deg, #dc2626, #b91c1c)',
                          boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4), inset 0 2px 4px rgba(255, 255, 255, 0.1)'
                        }}
                      >
                        <span className="text-lg">🛑</span>
                        <span className="text-xs leading-tight">E-STOP</span>
                      </button>
                    </div>
                  </div>

                  {/* Fine Movement Controls */}
                  <div className="space-y-2">
                    <h4 className="text-xs text-accent font-tactical">Fine Movement (TCP Coordinates)</h4>
                    
                    {/* Fine Movement Parameters */}
                    <div className="space-y-2">
                      {/* Step Size */}
                      <div className="space-y-1">
                        <label className="text-xs text-text-secondary">Step Size (mm)</label>
                        <div className="flex gap-2">
                          <Input
                            type="number"
                            value={fineStepSize}
                            onChange={(e) => {
                              const value = parseFloat(e.target.value);
                              if (!isNaN(value) && value > 0) {
                                setFineStepSize(value);
                                updateFineStepSize(value);
                              }
                            }}
                            step="0.1"
                            min="0.1"
                            className="text-xs bg-surface-dark border-accent/30 text-text-primary flex-1"
                          />
                          <div className="grid grid-cols-3 gap-1 flex-shrink-0">
                            <button onClick={() => {setFineStepSize(0.1); updateFineStepSize(0.1);}} className="tactical-button py-1 px-1 text-xs">0.1</button>
                            <button onClick={() => {setFineStepSize(1.0); updateFineStepSize(1.0);}} className="tactical-button py-1 px-1 text-xs">1.0</button>
                            <button onClick={() => {setFineStepSize(5.0); updateFineStepSize(5.0);}} className="tactical-button py-1 px-1 text-xs">5.0</button>
                          </div>
                        </div>
                      </div>

                      {/* Velocity and Acceleration */}
                      <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                          <label className="text-xs text-text-secondary">Velocity (m/s)</label>
                          <Input
                            type="number"
                            value={fineVelocity}
                            onChange={(e) => {
                              const value = parseFloat(e.target.value);
                              if (!isNaN(value) && value > 0) {
                                setFineVelocity(value);
                              }
                            }}
                            step="0.01"
                            min="0.01"
                            max="1.0"
                            className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs text-text-secondary">Acceleration (m/s²)</label>
                          <Input
                            type="number"
                            value={fineAcceleration}
                            onChange={(e) => {
                              const value = parseFloat(e.target.value);
                              if (!isNaN(value) && value > 0) {
                                setFineAcceleration(value);
                              }
                            }}
                            step="0.01"
                            min="0.01"
                            max="2.0"
                            className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                          />
                        </div>
                      </div>

                      {/* Rotation Angle */}
                      <div className="space-y-1">
                        <label className="text-xs text-text-secondary">Rotation Angle (°)</label>
                        <div className="flex gap-2">
                          <Input
                            type="number"
                            value={rotationAngle}
                            onChange={(e) => {
                              const value = parseFloat(e.target.value);
                              if (!isNaN(value) && value > 0) {
                                setRotationAngle(value);
                              }
                            }}
                            step="1"
                            min="1"
                            max="90"
                            className="text-xs bg-surface-dark border-accent/30 text-text-primary flex-1"
                          />
                          <div className="grid grid-cols-3 gap-1 flex-shrink-0">
                            <button onClick={() => setRotationAngle(1)} className="tactical-button py-1 px-1 text-xs">1°</button>
                            <button onClick={() => setRotationAngle(5)} className="tactical-button py-1 px-1 text-xs">5°</button>
                            <button onClick={() => setRotationAngle(15)} className="tactical-button py-1 px-1 text-xs">15°</button>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Fine Movement Buttons */}
                    <div className="space-y-2">
                      <div className="text-xs text-accent font-bold">Translation (mm)</div>
                      <div className="grid grid-cols-3 gap-1">
                        <button onClick={() => moveFine('x+')} className="tactical-button py-1 px-2 text-xs">+X</button>
                        <button onClick={() => moveFine('y+')} className="tactical-button py-1 px-2 text-xs">+Y</button>
                        <button onClick={() => moveFine('z+')} className="tactical-button py-1 px-2 text-xs">+Z</button>
                        <button onClick={() => moveFine('x-')} className="tactical-button py-1 px-2 text-xs">-X</button>
                        <button onClick={() => moveFine('y-')} className="tactical-button py-1 px-2 text-xs">-Y</button>
                        <button onClick={() => moveFine('z-')} className="tactical-button py-1 px-2 text-xs">-Z</button>
                      </div>
                    </div>

                    {/* Rotation Buttons */}
                    <div className="space-y-2">
                      <div className="text-xs text-accent font-bold">Rotation (°)</div>
                      <div className="grid grid-cols-3 gap-1">
                        <button onClick={() => moveRotation('rx+')} className="tactical-button py-1 px-2 text-xs">+Rx</button>
                        <button onClick={() => moveRotation('ry+')} className="tactical-button py-1 px-2 text-xs">+Ry</button>
                        <button onClick={() => moveRotation('rz+')} className="tactical-button py-1 px-2 text-xs">+Rz</button>
                        <button onClick={() => moveRotation('rx-')} className="tactical-button py-1 px-2 text-xs">-Rx</button>
                        <button onClick={() => moveRotation('ry-')} className="tactical-button py-1 px-2 text-xs">-Ry</button>
                        <button onClick={() => moveRotation('rz-')} className="tactical-button py-1 px-2 text-xs">-Rz</button>
                      </div>
                    </div>
                    
                    {/* Keyboard Hints */}
                    <div className="text-xs text-text-secondary bg-surface-dark/50 p-2 rounded">
                      <div className="font-bold text-accent mb-1">Keyboard Controls:</div>
                      <div>WASD/QE: Continuous movement</div>
                      <div>IJKL/UO: Translation ({fineStepSize}mm)</div>
                      <div>RF/TG/YH: Rotation Rx/Ry/Rz ({rotationAngle}°)</div>
                    </div>
                  </div>

                  {/* Quick Actions */}
                  <div className="grid grid-cols-2 gap-2">
                    <button 
                      onClick={moveToHomeJoints}
                      className="tactical-button py-1 px-2 rounded text-xs"
                    >
                      HOME JOINTS
                    </button>
                    <button 
                      onClick={() => setShowJointConfig(true)}
                      className="tactical-button py-1 px-2 rounded text-xs"
                    >
                      CONFIG JOINTS
                    </button>
                  </div>
                </div>
              )}
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
        onSave={updateHomeJoints}
      />
    </main>
  );
} 