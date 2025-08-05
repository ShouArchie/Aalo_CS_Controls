"use client";
import SettingsPopup from '@components/SettingsPopup';
import JointConfigPopup from '@components/JointConfigPopup';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { API_ENDPOINTS } from '@/lib/config';

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
  const [customTcp, setCustomTcp] = useState([-278.81, 0, 66.65, 0, 0, 0]); // [x, y, z, rx, ry, rz]
  
  // Global speed control
  const [globalSpeedPercent, setGlobalSpeedPercent] = useState(100);  // 0-100%
  const [baseSpeed, setBaseSpeed] = useState(0.05);  // Base speed for speedL (m/s)
  
  // Theme control
  const [isBeachsideTheme, setIsBeachsideTheme] = useState(false);

  // Blended spray pattern configuration
  const [coldSprayParams, setColdSprayParams] = useState({
    acceleration: "0.1",
    velocity: "0.1",
    blendRadius: "0.001",
    iterations: "7"
  });

  const [toolAligning, setToolAligning] = useState(false);

  // Responsive keystroke detection for WASD
  const [pressedKeys, setPressedKeys] = useState<Set<string>>(new Set());
  const [activeSpeedLKeys, setActiveSpeedLKeys] = useState<Set<string>>(new Set());
  


  // Conical spray paths configuration
  const [conicalSprayPaths, setConicalSprayPaths] = useState("");

  // Validation for cold spray parameters
  const isValidSprayParams = () => {
    const acc = parseFloat(coldSprayParams.acceleration);
    const vel = parseFloat(coldSprayParams.velocity);
    const blend = parseFloat(coldSprayParams.blendRadius);
    const iter = parseInt(coldSprayParams.iterations);
    
    return !isNaN(acc) && acc > 0 &&
           !isNaN(vel) && vel > 0 &&
           !isNaN(blend) && blend >= 0 &&
           !isNaN(iter) && iter > 0;
  };

  // Validation for conical spray paths
  const isValidConicalPaths = () => {
    if (!conicalSprayPaths.trim()) return false;
    
    try {
      const paths = JSON.parse(conicalSprayPaths);
      if (!Array.isArray(paths) || paths.length === 0 || paths.length > 4) return false;
      
      return paths.every(path => 
        typeof path === 'object' &&
        'tilt' in path && 'rev' in path && 'cycle' in path &&
        typeof path.tilt === 'number' && 
        typeof path.rev === 'number' && 
        typeof path.cycle === 'number'
      );
    } catch {
      return false;
    }
  };

  // TCP Presets
  const TCP_PRESETS: Record<number, { name: string; offset: number[] }> = {
    1: { name: "TCP Offset + 20mm", offset: [-278.81, 0.0, 66.65, 0.0, 0.0, 0.0] },
    2: { name: "TCP Center of Pipe + 20mm", offset: [-362.9475, 0.0, 66.65, 0.0, 0.0, 0.0] },
    3: { name: "TCP Offset + 0mm", offset: [-258.81, 0.0, 66.65, 0.0, 0.0, 0.0] },
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

  // Handle speedL movement (WASD/QE) - continuous sending while held
  const speedLIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Handle mouse hold movement - continuous sending while mouse held
  const mouseHoldIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [mouseHoldDirection, setMouseHoldDirection] = useState<string | null>(null);
  
  useEffect(() => {
    const speedLKeys = ['w', 's', 'a', 'd', 'q', 'e'];
    const currentSpeedLKeys = new Set([...pressedKeys].filter(key => speedLKeys.includes(key)));
    
    // Convert sets to sorted arrays for comparison
    const currentArray = [...currentSpeedLKeys].sort();
    const activeArray = [...activeSpeedLKeys].sort();
    
    // Check if speedL keys actually changed
    const keysChanged = currentArray.length !== activeArray.length || 
                       !currentArray.every((key, index) => key === activeArray[index]);
    
    if (keysChanged) {
      // Clear any existing interval
      if (speedLIntervalRef.current) {
        clearInterval(speedLIntervalRef.current);
        speedLIntervalRef.current = null;
      }
      
      if (currentSpeedLKeys.size === 0) {
        // No speedL keys pressed, send stop command
        if (activeSpeedLKeys.size > 0) {
          console.log('🛑 Stopping continuous speedL movement');
          stopRobot();
        }
      } else if (robotConnected) {
        // Start continuous speedL movement for the primary key
        const primaryKey = [...currentSpeedLKeys][0];
        console.log(`🚀 Starting continuous speedL: ${primaryKey}`);
        
        const sendSpeedLCommand = () => {
          switch (primaryKey) {
            case 'w':
              moveRobot('z+', 0.1);
              break;
            case 's':
              moveRobot('z-', 0.1);
              break;
            case 'a':
              moveRobot('y-', 0.1);
              break;
            case 'd':
              moveRobot('y+', 0.1);
              break;
            case 'q':
              moveRobot('x+', 0.1);
              break;
            case 'e':
              moveRobot('x-', 0.1);
              break;
          }
        };
        
        // Send initial command immediately
        sendSpeedLCommand();
        
        // Set up interval to continuously send speedL commands
        speedLIntervalRef.current = setInterval(sendSpeedLCommand, 150); // Send every 150ms
      }
      
      setActiveSpeedLKeys(currentSpeedLKeys);
    }
  }, [pressedKeys, robotConnected]);
  
  // Handle mouse hold continuous movement
  useEffect(() => {
    if (mouseHoldDirection && robotConnected) {
      // Send initial command immediately
      moveRobot(mouseHoldDirection, 0.1);
      
      // Set up interval for continuous movement
      mouseHoldIntervalRef.current = setInterval(() => {
        moveRobot(mouseHoldDirection, 0.1);
      }, 150); // Send every 150ms like WASD
    } else {
      // Clear interval and stop movement
      if (mouseHoldIntervalRef.current) {
        clearInterval(mouseHoldIntervalRef.current);
        mouseHoldIntervalRef.current = null;
      }
    }
    
    return () => {
      if (mouseHoldIntervalRef.current) {
        clearInterval(mouseHoldIntervalRef.current);
      }
    };
  }, [mouseHoldDirection, robotConnected]);

  // Clean up intervals on unmount
  useEffect(() => {
    return () => {
      if (speedLIntervalRef.current) {
        clearInterval(speedLIntervalRef.current);
      }
      if (mouseHoldIntervalRef.current) {
        clearInterval(mouseHoldIntervalRef.current);
      }
    };
  }, []);

  // Handle discrete fine movements (IJKL, UO, RFGTYH) - using ref to avoid infinite loops
  const processedKeysRef = useRef<Set<string>>(new Set());
  
  useEffect(() => {
    const fineMovementKeys = ['i', 'k', 'j', 'l', 'u', 'o', 'r', 'f', 't', 'g', 'y', 'h'];
    const newFineKeys = [...pressedKeys].filter(key => 
      fineMovementKeys.includes(key) && !processedKeysRef.current.has(key)
    );
    
    if (newFineKeys.length > 0 && robotConnected) {
      newFineKeys.forEach(key => {
        switch (key) {
          case 'i':
            moveFine('z+', fineStepSize);
            break;
          case 'k':
            moveFine('z-', fineStepSize);
            break;
          case 'j':
            moveFine('y-', fineStepSize);
            break;
          case 'l':
            moveFine('y+', fineStepSize);
            break;
          case 'u':
            moveFine('x+', fineStepSize);
            break;
          case 'o':
            moveFine('x-', fineStepSize);
            break;
          case 'r':
            moveRotation('rx+', rotationAngle);
            break;
          case 'f':
            moveRotation('rx-', rotationAngle);
            break;
          case 't':
            moveRotation('ry+', rotationAngle);
            break;
          case 'g':
            moveRotation('ry-', rotationAngle);
            break;
          case 'y':
            moveRotation('rz+', rotationAngle);
            break;
          case 'h':
            moveRotation('rz-', rotationAngle);
            break;
        }
        // Mark this key as processed
        processedKeysRef.current.add(key);
      });
    }
    
    // Remove released keys from processed set
    const currentFineKeys = [...pressedKeys].filter(key => fineMovementKeys.includes(key));
    processedKeysRef.current = new Set([...processedKeysRef.current].filter(key => currentFineKeys.includes(key)));
    
  }, [pressedKeys, robotConnected, fineStepSize, rotationAngle]);

  // Clear pressed keys when robot disconnects
  useEffect(() => {
    if (!robotConnected) {
      setPressedKeys(new Set());
      setActiveSpeedLKeys(new Set());
      processedKeysRef.current = new Set();
    }
  }, [robotConnected]);

  // Keyboard shortcuts for robot controls
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'F1') {
        event.preventDefault();
        setShowSettings(true);
      }
      // Spacebar for Emergency Stop (works even when not connected or typing)
      else if (event.key === ' ') {
        event.preventDefault();
        console.log('🚨 Emergency Stop triggered by SPACEBAR');
        stopRobot();
      }
      // WASD robot movement (only when robot is connected and not typing in input)
      else if (robotConnected && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        const key = event.key.toLowerCase();
        const movementKeys = ['w', 's', 'a', 'd', 'q', 'e', 'i', 'k', 'j', 'l', 'u', 'o', 'r', 'f', 't', 'g', 'y', 'h'];
        
        if (movementKeys.includes(key) && !event.repeat) {
          event.preventDefault();
          setPressedKeys(prev => new Set(prev).add(key));
        }
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      // Remove key from pressed keys set
      if (robotConnected && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        const key = event.key.toLowerCase();
        const movementKeys = ['w', 's', 'a', 'd', 'q', 'e', 'i', 'k', 'j', 'l', 'u', 'o', 'r', 'f', 't', 'g', 'y', 'h'];
        
        if (movementKeys.includes(key)) {
          event.preventDefault();
          setPressedKeys(prev => {
            const newSet = new Set(prev);
            newSet.delete(key);
            return newSet;
          });
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
      const response = await fetch(API_ENDPOINTS.ROBOT_CONNECT, {
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
      const response = await fetch(API_ENDPOINTS.ROBOT_DISCONNECT, {
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
      const response = await fetch(API_ENDPOINTS.ROBOT_HOME_JOINTS, {
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
      const response = await fetch(API_ENDPOINTS.ROBOT_CONFIG_HOME_JOINTS, {
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
      const response = await fetch(API_ENDPOINTS.ROBOT_THERMAL_TRACKING, {
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

  // Mouse hold movement handlers
  const startMouseHold = (direction: string) => {
    console.log(`🖱️ Starting mouse hold movement: ${direction}`);
    setMouseHoldDirection(direction);
  };

  const stopMouseHold = () => {
    console.log(`🖱️ Stopping mouse hold movement`);
    setMouseHoldDirection(null);
    stopRobot();
  };

  const moveRobot = async (direction: string, distance: number = 0.05) => {
    try {
      console.log(`🚀 Frontend moveRobot: direction=${direction}, speed_percent=${globalSpeedPercent}%, base_speed=${baseSpeed}`);
      const response = await fetch(API_ENDPOINTS.ROBOT_MOVE, {
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
      } else {
        // Update position after movement
        setTimeout(updateTcpPosition, 200);
      }
    } catch (error) {
      console.error('Failed to move robot:', error);
    }
  };

  const stopRobot = async () => {
    try {
      console.log('🛑 Frontend stopRobot called - sending immediate stop');
      
      // Send stop command without waiting for response to minimize delay
      fetch(API_ENDPOINTS.ROBOT_STOP, {
        method: 'POST'
      }).catch(error => {
        console.error('Failed to stop robot:', error);
      });
      
      // Also send a second stop command with a tiny delay for redundancy
      setTimeout(() => {
        fetch(API_ENDPOINTS.ROBOT_STOP, {
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
      
      const response = await fetch(API_ENDPOINTS.ROBOT_MOVE_FINE, {
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
      } else {
        // Update position after fine movement
        setTimeout(updateTcpPosition, 200);
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
      
      const response = await fetch(API_ENDPOINTS.ROBOT_MOVE_ROTATION, {
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
      } else {
        // Update position after rotation
        setTimeout(updateTcpPosition, 200);
      }
    } catch (error) {
      console.error('Failed to move robot rotation:', error);
    }
  };

  const updateTcpPosition = async () => {
    try {
      if (!robotConnected) {
        setRobotPosition('DISCONNECTED');
        return;
      }

              const response = await fetch(API_ENDPOINTS.ROBOT_TCP_POSITION);
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          const [x, y, z] = result.position_mm.map((val: number) => val.toFixed(1));
          const [rx, ry, rz] = result.rotation_deg.map((val: number) => val.toFixed(1));
          setRobotPosition(`${x},${y},${z} | ${rx}°,${ry}°,${rz}°`);
        } else {
          setRobotPosition('ERROR');
        }
      } else {
        setRobotPosition('FETCH_ERROR');
      }
    } catch (error) {
      console.error('Failed to get TCP position:', error);
      setRobotPosition('UNKNOWN');
    }
  };

  // TCP Position polling - placed after updateTcpPosition function definition
  useEffect(() => {
    let positionInterval: NodeJS.Timeout;
    
    if (robotConnected) {
      // Update position immediately when connected
      updateTcpPosition();
      
      // Set up polling every 2 seconds
      positionInterval = setInterval(updateTcpPosition, 2000);
    } else {
      setRobotPosition('DISCONNECTED');
    }
    
    return () => {
      if (positionInterval) {
        clearInterval(positionInterval);
      }
    };
  }, [robotConnected]);

  const updateFineStepSize = async (newStepSize: number) => {
    try {
              const response = await fetch(API_ENDPOINTS.ROBOT_CONFIG_STEP_SIZE, {
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
      
      const response = await fetch(API_ENDPOINTS.ROBOT_SET_TCP, {
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
        
        // Update position immediately after setting TCP
        setTimeout(updateTcpPosition, 100);
      } else {
        const error = await response.json();
        console.error('Failed to set TCP:', error.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to set TCP:', error);
    }
  };

  const executeColdSprayPattern = async () => {
    try {
      if (!robotConnected) {
        console.error('Robot not connected');
        return;
      }

      console.log(`🧊 Executing blended spray pattern with params:`, coldSprayParams);

      const response = await fetch(API_ENDPOINTS.ROBOT_COLD_SPRAY, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          acceleration: parseFloat(coldSprayParams.acceleration),
          velocity: parseFloat(coldSprayParams.velocity),
          blend_radius: parseFloat(coldSprayParams.blendRadius),
          iterations: parseInt(coldSprayParams.iterations)
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Blended spray pattern executed:`, result.message);
      } else {
        const error = await response.json();
        console.error('Failed to execute blended spray pattern:', error.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to execute blended spray pattern:', error);
    }
  };

  const executeToolAlignment = async () => {
    try {
      if (!robotConnected) {
        console.error('Robot not connected');
        return;
      }

      setToolAligning(true);
      console.log(`🔧 Executing tool alignment`);

      const response = await fetch(API_ENDPOINTS.ROBOT_ALIGN_TOOL, {
        method: 'POST'
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Tool alignment executed:`, result.message);
        
        // Alignment should complete quickly (translate + rotate)
        setTimeout(() => {
          setToolAligning(false);
          console.log('🏁 Tool alignment completed');
        }, 3000); // 3 seconds estimated duration
      } else {
        const error = await response.json();
        console.error('Failed to execute tool alignment:', error.error || 'Unknown error');
        setToolAligning(false);
      }
    } catch (error) {
      console.error('Failed to execute tool alignment:', error);
      setToolAligning(false);
    }
  };



  const executeConicalSprayPaths = async () => {
    try {
      if (!robotConnected) {
        console.error('Robot not connected');
        return;
      }

      if (!isValidConicalPaths()) {
        console.error('Invalid conical spray paths');
        return;
      }

      console.log(`🌀 Executing conical spray paths:`, conicalSprayPaths);

      const response = await fetch(API_ENDPOINTS.ROBOT_CONICAL_SPRAY, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spray_paths: conicalSprayPaths
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Conical spray paths executed:`, result.message);
      } else {
        const error = await response.json();
        console.error('Failed to execute conical spray paths:', error.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Failed to execute conical spray paths:', error);
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
      <div className="p-2 min-h-[calc(100vh-80px)] overflow-y-auto">
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
            <div className="space-y-2">
              {/* Status and Thermal Track Row */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Status:</span>
                  <span className={robotConnected ? 'text-success' : 'text-warning'}>{robotStatus}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Thermal Track:</span>
                  <span className={thermalTracking ? 'text-success' : 'text-text-secondary'}>
                    {thermalTracking ? 'ACTIVE' : 'INACTIVE'}
                  </span>
                </div>
              </div>
              
              {/* TCP Position Row - Full Width */}
              <div className="bg-surface-dark/30 rounded p-2 border border-accent/20">
                <div className="flex justify-between items-center">
                  <span className="text-text-secondary text-sm font-bold">TCP Position:</span>
                  <span className="text-text-primary text-sm font-mono bg-black/20 px-2 py-1 rounded border">{robotPosition}</span>
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* LEFT HALF: SpeedL Controls */}
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-3">
            <div className="flex items-center gap-2">
              <div className="status-indicator bg-warning"></div>
              <h3 className="text-lg font-tactical text-accent font-medium">SpeedL Continuous Movement</h3>
            </div>

            {robotConnected && (
              <>
                {/* Speed Configuration */}
                <div className="space-y-2 border-b border-accent/20 pb-3">
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
                <div className="space-y-3">
                  <h4 className="text-sm text-accent font-tactical">Continuous Movement (Base Coordinates)</h4>
                  
                  {/* Keyboard Controls Info */}
                  <div className="text-xs text-text-secondary bg-surface-dark/30 p-2 rounded">
                    <span className="text-accent font-bold">⌨️ Responsive Keys:</span><br/>
                    <span className="text-blue-400">• SpeedL (Continuous Stream):</span> WASD (XYZ), QE (±X) - Hold for continuous speedL commands<br/>
                    <span className="text-green-400">• Fine (Discrete):</span> IJKL (XYZ), UO (±X), RFGTYH (Rotations)<br/>
                    <span className="text-red-400">• Emergency Stop:</span> SPACEBAR (immediate stop)
                  </div>
                  
                  {/* Active Keys Indicator */}
                  {pressedKeys.size > 0 && (
                    <div className="bg-accent/10 border border-accent/20 rounded p-2">
                      <div className="text-xs text-text-secondary mb-1">Active Keys:</div>
                      <div className="flex gap-1 flex-wrap">
                        {Array.from(pressedKeys).map(key => {
                          const isSpeedL = ['w', 's', 'a', 'd', 'q', 'e'].includes(key);
                          const isFine = ['i', 'k', 'j', 'l', 'u', 'o', 'r', 'f', 't', 'g', 'y', 'h'].includes(key);
                          return (
                            <span 
                              key={key} 
                              className={`px-2 py-1 rounded text-xs font-mono font-bold ${
                                isSpeedL 
                                  ? 'bg-blue-500/20 text-blue-400 animate-pulse' 
                                  : isFine 
                                    ? 'bg-green-500/20 text-green-400' 
                                    : 'bg-accent/20 text-accent'
                              }`}
                            >
                              {key.toUpperCase()}
                              {isSpeedL && ' (SpeedL)'}
                              {isFine && ' (Fine)'}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  {/* Large Movement Buttons */}
                  <div className="grid grid-cols-3 gap-3">
                    <button 
                                      onMouseDown={() => startMouseHold('x+')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      +X
                    </button>
                    <button 
                                      onMouseDown={() => startMouseHold('y+')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      +Y
                    </button>
                    <button 
                                      onMouseDown={() => startMouseHold('z+')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      +Z
                    </button>
                    <button 
                                      onMouseDown={() => startMouseHold('x-')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      -X
                    </button>
                    <button 
                                      onMouseDown={() => startMouseHold('y-')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      -Y
                    </button>
                    <button 
                                      onMouseDown={() => startMouseHold('z-')}
                onMouseUp={stopMouseHold}
                      onMouseLeave={stopRobot}
                      className="tactical-button py-3 px-3 text-base font-bold select-none"
                    >
                      -Z
                    </button>
                  </div>
                  
                  {/* Emergency Stop Button */}
                  <div className="flex justify-center mt-3">
                    <button 
                      onClick={stopRobot}
                      className="w-24 h-24 bg-red-600 hover:bg-red-700 text-white font-bold text-base border-4 border-red-500 shadow-xl hover:shadow-red-500/50 transition-all duration-200 flex flex-col items-center justify-center gap-1 active:scale-95 rounded-lg"
                      style={{
                        background: 'linear-gradient(145deg, #dc2626, #b91c1c)',
                        boxShadow: '0 8px 20px rgba(239, 68, 68, 0.4), inset 0 4px 8px rgba(255, 255, 255, 0.1)'
                      }}
                    >
                      <span className="text-2xl">🛑</span>
                      <span className="text-xs leading-tight">E-STOP</span>
                    </button>
                  </div>



                  {/* Keyboard Hints */}
                  <div className="text-xs text-text-secondary bg-surface-dark/50 p-2 rounded">
                    <div className="font-bold text-accent mb-1">Keyboard Controls:</div>
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
          <div className="bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-3">
            <div className="flex items-center gap-2">
              <div className="status-indicator bg-info"></div>
              <h3 className="text-lg font-tactical text-accent font-medium">Fine Movement (mm precision)</h3>
            </div>

            {robotConnected && (
              <>
                {/* TCP Configuration */}
                <div className="space-y-2 border-b border-accent/20 pb-3">
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
                          1: TCP Offset + 20mm (-278.81, 0, 60.3)
                        </SelectItem>
                        <SelectItem value="2" className="text-sm text-text-primary hover:bg-accent/20">
                          2: TCP Center of Pipe + 20mm (-362.9475, 0.0, 60.3)
                        </SelectItem>
                        <SelectItem value="3" className="text-sm text-text-primary hover:bg-accent/20">
                          3: TCP Offset + 0mm (-258.81, 0.0, 60.3)
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
                          {customTcp.map((value, index) => {
                            // Convert radians to degrees for display (rotation values)
                            const displayValue = index >= 3 ? (value * 180 / Math.PI) : value;
                            
                            return (
                              <Input
                                key={index}
                                type="number"
                                value={displayValue}
                                onChange={(e) => {
                                  const newTcp = [...customTcp];
                                  const inputValue = e.target.value;
                                  if (inputValue === '' || inputValue === '-') {
                                    // Allow empty input or just minus sign for negative numbers
                                    newTcp[index] = 0;
                                  } else {
                                    let parsedValue = parseFloat(inputValue);
                                    if (!isNaN(parsedValue)) {
                                      // Convert degrees to radians for rotation values (indices 3, 4, 5)
                                      if (index >= 3) {
                                        parsedValue = parsedValue * Math.PI / 180;
                                      }
                                      newTcp[index] = parsedValue;
                                    } else {
                                      newTcp[index] = 0;
                                    }
                                  }
                                  setCustomTcp(newTcp);
                                }}
                                placeholder={index < 3 ? ['X', 'Y', 'Z'][index] : ['Rx°', 'Ry°', 'Rz°'][index - 3]}
                                className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                                step={index < 3 ? "0.1" : "1"}
                              />
                            );
                          })}
                        </div>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => setCustomTcp([-278.81, 0, 60.3, 0, 0, 0])}
                            className="tactical-button py-1 px-2 rounded text-xs flex-1"
                          >
                            Reset to Primary
                          </button>
                          <button 
                            onClick={() => setTcp(5)}
                            className="tactical-button py-1 px-2 rounded text-xs flex-1"
                          >
                            Apply Custom TCP
                          </button>
                        </div>
                        <div className="text-xs text-text-secondary space-y-1">
                          <div>Position in mm (negative values allowed), Rotation in degrees (auto-converted to radians)</div>
                          <div className="text-accent">Common angles: 90° = π/2, 180° = π, -90° = -π/2</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Fine Movement Parameters */}
                <div className="space-y-2 border-b border-accent/20 pb-3">
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
                <div className="space-y-2">
                  <div className="space-y-3">
                    <div className="text-sm text-accent font-bold">Translation ({fineStepSize}mm steps)</div>
                    <div className="grid grid-cols-3 gap-2">
                      <button onClick={() => moveFine('x+')} className="tactical-button py-2 px-2 text-sm font-semibold">+X</button>
                      <button onClick={() => moveFine('y+')} className="tactical-button py-2 px-2 text-sm font-semibold">+Y</button>
                      <button onClick={() => moveFine('z+')} className="tactical-button py-2 px-2 text-sm font-semibold">+Z</button>
                      <button onClick={() => moveFine('x-')} className="tactical-button py-2 px-2 text-sm font-semibold">-X</button>
                      <button onClick={() => moveFine('y-')} className="tactical-button py-2 px-2 text-sm font-semibold">-Y</button>
                      <button onClick={() => moveFine('z-')} className="tactical-button py-2 px-2 text-sm font-semibold">-Z</button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="text-sm text-accent font-bold">Rotation ({rotationAngle}° steps)</div>
                    <div className="grid grid-cols-3 gap-2">
                      <button onClick={() => moveRotation('rx+')} className="tactical-button py-2 px-2 text-sm font-semibold">+Rx</button>
                      <button onClick={() => moveRotation('ry+')} className="tactical-button py-2 px-2 text-sm font-semibold">+Ry</button>
                      <button onClick={() => moveRotation('rz+')} className="tactical-button py-2 px-2 text-sm font-semibold">+Rz</button>
                      <button onClick={() => moveRotation('rx-')} className="tactical-button py-2 px-2 text-sm font-semibold">-Rx</button>
                      <button onClick={() => moveRotation('ry-')} className="tactical-button py-2 px-2 text-sm font-semibold">-Ry</button>
                      <button onClick={() => moveRotation('rz-')} className="tactical-button py-2 px-2 text-sm font-semibold">-Rz</button>
                    </div>
                  </div>
                  
                  {/* Keyboard Hints */}
                  <div className="text-xs text-text-secondary bg-surface-dark/50 p-2 rounded">
                    <div className="font-bold text-accent mb-1">Keyboard Controls:</div>
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

        {/* Blended Spray Pattern Controls */}
        <div className="mt-3 bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <div className="status-indicator bg-info"></div>
            <h3 className="text-lg font-tactical text-accent font-medium">Blended Spray Pattern</h3>
          </div>

          {robotConnected && (
            <>
              {/* Blended Spray Parameters */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Acceleration (m/s²)</label>
                  <Input
                    type="number"
                    value={coldSprayParams.acceleration}
                    onChange={(e) => setColdSprayParams(prev => ({
                      ...prev,
                      acceleration: e.target.value
                    }))}
                    step="0.01"
                    min="0"
                    max="2.0"
                    className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Velocity (m/s)</label>
                  <Input
                    type="number"
                    value={coldSprayParams.velocity}
                    onChange={(e) => setColdSprayParams(prev => ({
                      ...prev,
                      velocity: e.target.value
                    }))}
                    step="0.01"
                    min="0"
                    max="1.0"
                    className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Blend Radius (m)</label>
                  <Input
                    type="number"
                    value={coldSprayParams.blendRadius}
                    onChange={(e) => setColdSprayParams(prev => ({
                      ...prev,
                      blendRadius: e.target.value
                    }))}
                    step="0.0001"
                    min="0"
                    max="0.01"
                    className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Iterations</label>
                  <Input
                    type="number"
                    value={coldSprayParams.iterations}
                    onChange={(e) => setColdSprayParams(prev => ({
                      ...prev,
                      iterations: e.target.value
                    }))}
                    step="1"
                    min="0"
                    max="50"
                    className="text-sm bg-surface-dark border-accent/30 text-text-primary"
                  />
                </div>
              </div>

              {/* Preset Buttons */}
              <div className="space-y-2">
                <label className="text-sm text-text-secondary">Quick Presets</label>
                <div className="flex gap-2 flex-wrap">
                  <button 
                    onClick={() => setColdSprayParams({
                      acceleration: "0.05",
                      velocity: "0.05",
                      blendRadius: "0.001",
                      iterations: "5"
                    })}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Slow & Precise
                  </button>
                  <button 
                    onClick={() => setColdSprayParams({
                      acceleration: "0.1",
                      velocity: "0.1",
                      blendRadius: "0.001",
                      iterations: "7"
                    })}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Standard
                  </button>
                  <button 
                    onClick={() => setColdSprayParams({
                      acceleration: "0.2",
                      velocity: "0.2",
                      blendRadius: "0.002",
                      iterations: "10"
                    })}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Fast & Coverage
                  </button>
                </div>
              </div>

              {/* Align and Execute Buttons */}
              <div className="space-y-3">
                {/* Align Tool Button */}
                <div className="flex justify-center">
                  <button 
                    onClick={executeToolAlignment}
                    disabled={toolAligning}
                    className={`tactical-button py-3 px-6 text-base font-bold rounded-lg ${
                      toolAligning 
                        ? 'opacity-50 cursor-not-allowed' 
                        : 'bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700'
                    }`}
                  >
                    {toolAligning ? (
                      <div className="flex items-center gap-2">
                        <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                        ALIGNING TOOL...
                      </div>
                    ) : (
                      '🔧 ALIGN TOOL FOR SPRAY PATTERN'
                    )}
                  </button>
                </div>

                {/* Execute Pattern Button */}
                <div className="flex justify-center">
                                    <button
                    onClick={executeColdSprayPattern}
                    disabled={toolAligning || !isValidSprayParams()}
                    className={`tactical-button py-4 px-8 text-lg font-bold rounded-lg ${
                      toolAligning || !isValidSprayParams()
                        ? 'opacity-50 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700'
                    }`}
                  >
                    🧊 EXECUTE BLENDED SPRAY PATTERN
                  </button>
                </div>
              </div>

              {/* Pattern Info */}
              <div className="text-xs text-text-secondary bg-surface-dark/50 p-3 rounded">
                <div className="font-bold text-accent mb-2">Workflow:</div>
                <div>1. <span className="text-amber-400">ALIGN TOOL:</span> 20mm Y translation + 13.5° Y rotation</div>
                <div>2. <span className="text-cyan-400">EXECUTE PATTERN:</span> Blended spray (forward/reverse cycles)</div>
                <div>• Movement distance: 50mm back-and-forth in Y direction</div>
                <div>• Rotation increment: 1.36° per step</div>
                <div>• Pattern structure: 5 forward + 5 reverse cycles per iteration</div>
                <div>• Total iterations: {coldSprayParams.iterations || '0'} cycles</div>
              </div>
            </>
          )}

          {!robotConnected && (
            <div className="flex items-center justify-center h-32">
              <div className="text-center text-text-secondary">
                <div className="text-4xl mb-4">🧊</div>
                <div className="text-lg">Robot Not Connected</div>
                <div className="text-sm">Connect robot to use cold spray pattern</div>
              </div>
            </div>
          )}
        </div>

        {/* Conical Spray Paths Controls */}
        <div className="mt-3 bg-black/10 backdrop-blur-sm rounded border border-accent/15 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <div className="status-indicator bg-warning"></div>
            <h3 className="text-lg font-tactical text-accent font-medium">Conical Spray Paths</h3>
          </div>

          {robotConnected && (
            <>
              {/* Input Field */}
              <div className="space-y-2">
                <label className="text-sm text-text-secondary">
                  Spray Path Configuration (1-4 paths)
                </label>
                <textarea
                  value={conicalSprayPaths}
                  onChange={(e) => setConicalSprayPaths(e.target.value)}
                  placeholder='[{"tilt": 15, "rev": 4, "cycle": 0.0475}, {"tilt": 10, "rev": 4, "cycle": 0.0475}]'
                  className="w-full h-24 text-sm bg-surface-dark border-accent/30 text-text-primary p-3 rounded font-mono"
                />
              </div>

              {/* Example Buttons */}
              <div className="space-y-2">
                <label className="text-sm text-text-secondary">Quick Examples</label>
                <div className="flex gap-2 flex-wrap">
                  <button 
                    onClick={() => setConicalSprayPaths('[{"tilt": 10, "rev": 2, "cycle": 0.015}]')}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Single Path
                  </button>
                  <button 
                    onClick={() => setConicalSprayPaths('[{"tilt": 5, "rev": 2, "cycle": 0.015}, {"tilt": 10, "rev": 2, "cycle": 0.015}]')}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Dual Path
                  </button>
                  <button 
                    onClick={() => setConicalSprayPaths('[{"tilt": 3, "rev": 2, "cycle": 0.015}, {"tilt": 5, "rev": 2, "cycle": 0.015}, {"tilt": 8, "rev": 2, "cycle": 0.015}')}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Tri Path
                  </button>
                  <button 
                    onClick={() => setConicalSprayPaths('[{"tilt": 3, "rev": 2, "cycle": 0.015}, {"tilt": 5, "rev": 2, "cycle": 0.015}, {"tilt": 8, "rev": 2, "cycle": 0.015}, {"tilt": 10, "rev": 2, "cycle": 0.015}]')}
                    className="tactical-button py-2 px-3 text-sm"
                  >
                    Quad Path
                  </button>
                </div>
              </div>

              {/* Execute Button */}
              <div className="flex justify-center">
                <button
                  onClick={executeConicalSprayPaths}
                  disabled={!isValidConicalPaths() || toolAligning}
                  className={`tactical-button py-3 px-6 text-base font-bold rounded-lg ${
                    !isValidConicalPaths() || toolAligning
                      ? 'opacity-50 cursor-not-allowed'
                      : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700'
                  }`}
                >
                  🌀 EXECUTE CONICAL SPRAY PATHS
                </button>
              </div>

              {/* Info */}
              <div className="text-xs text-text-secondary bg-surface-dark/50 p-3 rounded">
                <div className="font-bold text-accent mb-2">Pattern Info:</div>
                <div>• <span className="text-purple-400">Steps:</span> Always 180 × revolutions</div>
                <div>• <span className="text-pink-400">Parameters:</span> tilt (degrees), rev (revolutions), cycle (seconds)</div>
                <div>• <span className="text-blue-400">Paths:</span> {isValidConicalPaths() ? JSON.parse(conicalSprayPaths).length : 0}/4 configured</div>
                {isValidConicalPaths() && (
                  <div>• <span className="text-green-400">Total Steps:</span> {JSON.parse(conicalSprayPaths).reduce((total: number, path: any) => total + (path.rev * 180), 0)}</div>
                )}
              </div>
            </>
          )}

          {!robotConnected && (
            <div className="flex items-center justify-center h-32">
              <div className="text-center text-text-secondary">
                <div className="text-4xl mb-4">🌀</div>
                <div className="text-lg">Robot Not Connected</div>
                <div className="text-sm">Connect robot to use conical spray paths</div>
              </div>
            </div>
          )}
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