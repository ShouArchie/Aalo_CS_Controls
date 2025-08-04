"use client";
import SettingsPopup from '@components/SettingsPopup';
import JointConfigPopup from '@components/JointConfigPopup';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ControlsPage() {
  const router = useRouter();
  const [showSettings, setShowSettings] = useState(false);
  
  // Robot control states
  const [robotIp, setRobotIp] = useState('192.168.10.205');
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

  // Navigation helper
  const navigateTo = (path: string) => {
    router.push(path);
  };

  // Keyboard shortcuts for robot controls
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'F1') {
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
  }, [robotConnected, fineStepSize, globalSpeedPercent, baseSpeed, rotationAngle]);

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
            <div className={`status-indicator ${robotConnected ? 'bg-success' : 'bg-warning'}`}></div>
            <h1 className="text-lg font-tactical font-semibold text-accent">
              UR-10E Robot Controls
            </h1>
            <div className="text-xs text-text-secondary font-mono">
              {robotConnected ? 'ROBOT.ONLINE' : 'ROBOT.OFFLINE'} | CONTROL.ACTIVE
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
              onClick={() => navigateTo('/views')}
              className="tactical-button px-2 py-1 rounded text-xs"
              title="Camera Views"
            >
              VIEWS
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

      {/* Main Control Layout */}
      <div className="p-2 h-[calc(100vh-80px)]">
        {/* Robot Connection & Status Header */}
        <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 mb-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Connection Controls */}
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
                  className={`tactical-button px-3 py-1 rounded text-xs whitespace-nowrap ${robotConnected ? 'bg-danger hover:bg-danger/80' : ''}`}
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

            {/* Quick Actions */}
            <div className="flex gap-2">
              <button 
                onClick={moveToHomeJoints}
                className="tactical-button py-1 px-3 rounded text-xs flex-1"
                disabled={!robotConnected}
              >
                HOME JOINTS
              </button>
              <button 
                onClick={() => setShowJointConfig(true)}
                className="tactical-button py-1 px-3 rounded text-xs flex-1"
              >
                CONFIG JOINTS
              </button>
            </div>
          </div>
        </div>

        {/* Two Column Layout: SpeedL (Left) | Fine Movement (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100%-120px)]">
          {/* LEFT HALF: SpeedL Controls */}
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-4 space-y-4 overflow-y-auto">
            <div className="flex items-center gap-2">
              <div className="status-indicator bg-warning"></div>
              <h3 className="text-lg font-tactical text-accent font-medium">SpeedL Continuous Movement</h3>
            </div>

            {robotConnected && (
              <>
                {/* Speed Configuration */}
                <div className="space-y-4 border-b border-accent/20 pb-4">
                  <h4 className="text-sm text-accent font-tactical">Speed Configuration</h4>
                  
                  {/* Base Speed Input */}
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Base Speed (m/s)</label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        value={baseSpeed}
                        onChange={(e) => {
                          const inputValue = e.target.value;
                          if (inputValue === '' || inputValue === '0') {
                            setBaseSpeed(0.01);
                          } else {
                            const value = parseFloat(inputValue);
                            if (!isNaN(value) && value > 0) {
                              setBaseSpeed(Math.min(Math.max(value, 0.0001), 1.0));
                            }
                          }
                        }}
                        step="0.01"
                        min="0.01"
                        max="1.0"
                        className="text-sm bg-surface-dark border-accent/30 text-text-primary flex-1"
                      />
                      <div className="flex gap-1">
                        <button onClick={() => setBaseSpeed(0.05)} className="tactical-button py-2 px-3 text-sm">0.05</button>
                        <button onClick={() => setBaseSpeed(0.1)} className="tactical-button py-2 px-3 text-sm">0.1</button>
                        <button onClick={() => setBaseSpeed(0.2)} className="tactical-button py-2 px-3 text-sm">0.2</button>
                      </div>
                    </div>
                  </div>

                  {/* Global Speed Control */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-text-secondary">Global Speed Multiplier</span>
                      <span className="text-accent font-bold">{globalSpeedPercent}%</span>
                    </div>
                    <div className="flex gap-3 items-center">
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
                        <button onClick={() => setGlobalSpeedPercent(25)} className="tactical-button py-1 px-2 text-xs">25%</button>
                        <button onClick={() => setGlobalSpeedPercent(50)} className="tactical-button py-1 px-2 text-xs">50%</button>
                        <button onClick={() => setGlobalSpeedPercent(100)} className="tactical-button py-1 px-2 text-xs">100%</button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Continuous Movement Controls */}
                <div className="space-y-4">
                  <h4 className="text-sm text-accent font-tactical">Continuous Movement (Base Coordinates)</h4>
                  
                  {/* Large Movement Buttons */}
                  <div className="grid grid-cols-3 gap-3">
                    <button 
                      onMouseDown={() => moveRobot('x+')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      +X
                    </button>
                    <button 
                      onMouseDown={() => moveRobot('y+')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      +Y
                    </button>
                    <button 
                      onMouseDown={() => moveRobot('z+')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      +Z
                    </button>
                    <button 
                      onMouseDown={() => moveRobot('x-')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      -X
                    </button>
                    <button 
                      onMouseDown={() => moveRobot('y-')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      -Y
                    </button>
                    <button 
                      onMouseDown={() => moveRobot('z-')} 
                      onMouseUp={stopRobot}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-4 px-4 text-lg font-bold select-none"
                    >
                      -Z
                    </button>
                  </div>
                  
                  {/* Emergency Stop Button */}
                  <div className="flex justify-center mt-6">
                    <button 
                      onClick={stopRobot}
                      className="w-32 h-32 bg-red-600 hover:bg-red-700 text-white font-bold text-lg border-4 border-red-500 shadow-xl hover:shadow-red-500/50 transition-all duration-200 flex flex-col items-center justify-center gap-2 active:scale-95 rounded-lg"
                      style={{
                        background: 'linear-gradient(145deg, #dc2626, #b91c1c)',
                        boxShadow: '0 8px 20px rgba(239, 68, 68, 0.4), inset 0 4px 8px rgba(255, 255, 255, 0.1)'
                      }}
                    >
                      <span className="text-3xl">🛑</span>
                      <span className="text-sm leading-tight">EMERGENCY<br/>STOP</span>
                    </button>
                  </div>

                  {/* Keyboard Hints */}
                  <div className="text-sm text-text-secondary bg-surface-dark/50 p-3 rounded">
                    <div className="font-bold text-accent mb-2">Keyboard Controls:</div>
                    <div>WASD/QE: Continuous movement (hold keys)</div>
                    <div>Release keys to stop movement</div>
                  </div>
                </div>
              </>
            )}

            {!robotConnected && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-text-secondary">
                  <div className="text-4xl mb-4">🤖</div>
                  <div className="text-lg">Robot Not Connected</div>
                  <div className="text-sm">Connect robot to use SpeedL controls</div>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT HALF: Fine Movement Controls */}
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-4 space-y-4 overflow-y-auto">
            <div className="flex items-center gap-2">
              <div className="status-indicator bg-info"></div>
              <h3 className="text-lg font-tactical text-accent font-medium">Fine Movement (mm precision)</h3>
            </div>

            {robotConnected && (
              <>
                {/* TCP Configuration */}
                <div className="space-y-3 border-b border-accent/20 pb-4">
                  <label className="text-sm text-accent font-tactical">TCP Configuration</label>
                  <div className="space-y-2">
                    <Select 
                      value={selectedTcp.toString()} 
                      onValueChange={(value) => {
                        const tcpId = parseInt(value);
                        setTcp(tcpId);
                      }}
                    >
                      <SelectTrigger className="text-sm bg-surface-dark border-accent/30 text-text-primary">
                        <SelectValue placeholder="Select TCP" />
                      </SelectTrigger>
                      <SelectContent className="bg-surface-dark border-accent/30">
                        <SelectItem value="1" className="text-sm text-text-primary hover:bg-accent/20">
                          1: Primary TCP (-278.81, 0, 60.3)
                        </SelectItem>
                        <SelectItem value="2" className="text-sm text-text-primary hover:bg-accent/20">
                          2: Secondary TCP (Temporary)
                        </SelectItem>
                        <SelectItem value="3" className="text-sm text-text-primary hover:bg-accent/20">
                          3: Tertiary TCP (Temporary)
                        </SelectItem>
                        <SelectItem value="4" className="text-sm text-text-primary hover:bg-accent/20">
                          4: No TCP (Base Coordinates)
                        </SelectItem>
                        <SelectItem value="5" className="text-sm text-text-primary hover:bg-accent/20">
                          5: Custom TCP
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    
                    {/* Custom TCP Input */}
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

                {/* Fine Movement Parameters */}
                <div className="space-y-4 border-b border-accent/20 pb-4">
                  <h4 className="text-sm text-accent font-tactical">Movement Parameters</h4>
                  
                  {/* Step Size */}
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Step Size (mm)</label>
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
                        className="text-sm bg-surface-dark border-accent/30 text-text-primary flex-1"
                      />
                      <div className="grid grid-cols-3 gap-1 flex-shrink-0">
                        <button onClick={() => {setFineStepSize(0.1); updateFineStepSize(0.1);}} className="tactical-button py-2 px-2 text-xs">0.1</button>
                        <button onClick={() => {setFineStepSize(1.0); updateFineStepSize(1.0);}} className="tactical-button py-2 px-2 text-xs">1.0</button>
                        <button onClick={() => {setFineStepSize(5.0); updateFineStepSize(5.0);}} className="tactical-button py-2 px-2 text-xs">5.0</button>
                      </div>
                    </div>
                  </div>

                  {/* Velocity and Acceleration */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <label className="text-sm text-text-secondary">Velocity (m/s)</label>
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
                        className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-text-secondary">Acceleration (m/s²)</label>
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
                        className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                      />
                    </div>
                  </div>

                  {/* Rotation Angle */}
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Rotation Angle (°)</label>
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
                        className="text-sm bg-surface-dark border-accent/30 text-text-primary flex-1"
                      />
                      <div className="grid grid-cols-3 gap-1 flex-shrink-0">
                        <button onClick={() => setRotationAngle(1)} className="tactical-button py-2 px-2 text-xs">1°</button>
                        <button onClick={() => setRotationAngle(5)} className="tactical-button py-2 px-2 text-xs">5°</button>
                        <button onClick={() => setRotationAngle(15)} className="tactical-button py-2 px-2 text-xs">15°</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Fine Movement Buttons */}
                <div className="space-y-4">
                  <div className="space-y-3">
                    <div className="text-sm text-accent font-bold">Translation ({fineStepSize}mm steps)</div>
                    <div className="grid grid-cols-3 gap-2">
                      <button onClick={() => moveFine('x+')} className="tactical-button py-3 px-3 text-sm font-semibold">+X</button>
                      <button onClick={() => moveFine('y+')} className="tactical-button py-3 px-3 text-sm font-semibold">+Y</button>
                      <button onClick={() => moveFine('z+')} className="tactical-button py-3 px-3 text-sm font-semibold">+Z</button>
                      <button onClick={() => moveFine('x-')} className="tactical-button py-3 px-3 text-sm font-semibold">-X</button>
                      <button onClick={() => moveFine('y-')} className="tactical-button py-3 px-3 text-sm font-semibold">-Y</button>
                      <button onClick={() => moveFine('z-')} className="tactical-button py-3 px-3 text-sm font-semibold">-Z</button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="text-sm text-accent font-bold">Rotation ({rotationAngle}° steps)</div>
                    <div className="grid grid-cols-3 gap-2">
                      <button onClick={() => moveRotation('rx+')} className="tactical-button py-3 px-3 text-sm font-semibold">+Rx</button>
                      <button onClick={() => moveRotation('ry+')} className="tactical-button py-3 px-3 text-sm font-semibold">+Ry</button>
                      <button onClick={() => moveRotation('rz+')} className="tactical-button py-3 px-3 text-sm font-semibold">+Rz</button>
                      <button onClick={() => moveRotation('rx-')} className="tactical-button py-3 px-3 text-sm font-semibold">-Rx</button>
                      <button onClick={() => moveRotation('ry-')} className="tactical-button py-3 px-3 text-sm font-semibold">-Ry</button>
                      <button onClick={() => moveRotation('rz-')} className="tactical-button py-3 px-3 text-sm font-semibold">-Rz</button>
                    </div>
                  </div>
                  
                  {/* Keyboard Hints */}
                  <div className="text-sm text-text-secondary bg-surface-dark/50 p-3 rounded">
                    <div className="font-bold text-accent mb-2">Keyboard Controls:</div>
                    <div>IJKL/UO: Translation ({fineStepSize}mm)</div>
                    <div>RF/TG/YH: Rotation Rx/Ry/Rz ({rotationAngle}°)</div>
                  </div>
                </div>
              </>
            )}

            {!robotConnected && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-text-secondary">
                  <div className="text-4xl mb-4">🎯</div>
                  <div className="text-lg">Robot Not Connected</div>
                  <div className="text-sm">Connect robot to use fine movement controls</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Bottom section for future additions */}
        <div className="mt-4 h-16 bg-black/5 backdrop-blur-sm rounded border border-accent/10 p-3 flex items-center justify-center">
          <div className="text-text-secondary text-sm font-mono">
            [ RESERVED SPACE FOR FUTURE CONTROLS ]
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