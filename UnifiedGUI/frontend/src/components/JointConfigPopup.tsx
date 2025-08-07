'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { API_ENDPOINTS } from '@/lib/config';

interface JointConfigPopupProps {
  isOpen: boolean;
  onClose: () => void;
  homeJoints: number[];
  onUpdate: (joints: number[]) => void;
  onSave: () => void;
  onSaveCurrentAsHome: () => void;
}

export default function JointConfigPopup({ 
  isOpen, 
  onClose, 
  homeJoints, 
  onUpdate, 
  onSave,
  onSaveCurrentAsHome
}: JointConfigPopupProps) {
  // Store as strings to allow empty values during editing
  const [localJoints, setLocalJoints] = useState(homeJoints.map(j => j.toString()));
  
  // State for current robot joint angles
  const [currentRobotJoints, setCurrentRobotJoints] = useState<number[]>([]);
  const [loadingCurrentJoints, setLoadingCurrentJoints] = useState(false);

  // Sync local joints when popup opens with new homeJoints values
  if (isOpen && localJoints.length !== homeJoints.length) {
    setLocalJoints(homeJoints.map(j => j.toString()));
  }

  // Fetch current robot joint angles when popup opens
  useEffect(() => {
    if (isOpen) {
      fetchCurrentJoints();
    }
  }, [isOpen]);

  const fetchCurrentJoints = async () => {
    try {
      setLoadingCurrentJoints(true);
      const response = await fetch(API_ENDPOINTS.ROBOT_CURRENT_JOINTS);
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setCurrentRobotJoints(result.joints_deg);
        } else {
          console.error('❌ Failed to get current joints:', result.error);
          setCurrentRobotJoints([]); // Clear on error
        }
      } else {
        console.error('❌ HTTP error getting current joints:', response.status);
        setCurrentRobotJoints([]); // Clear on error
      }
    } catch (error) {
      console.error('❌ Failed to fetch current joints:', error);
      setCurrentRobotJoints([]); // Clear on error
    } finally {
      setLoadingCurrentJoints(false);
    }
  };

  if (!isOpen) return null;

  // Validation: check if all joints are valid numbers
  const areAllJointsValid = () => {
    return localJoints.every(joint => {
      const trimmed = joint.trim();
      return trimmed !== '' && !isNaN(parseFloat(trimmed));
    });
  };

  const handleJointChange = (index: number, value: string) => {
    // Allow empty values and any input during editing
    const newJoints = [...localJoints];
    newJoints[index] = value;
    setLocalJoints(newJoints);
    
    // Only update parent if all values are valid numbers
    const allValid = newJoints.every(joint => {
      const trimmed = joint.trim();
      return trimmed !== '' && !isNaN(parseFloat(trimmed));
    });
    
    if (allValid) {
      const numericJoints = newJoints.map(j => parseFloat(j.trim()));
      onUpdate(numericJoints);
    }
  };

  const handleSave = () => {
    if (areAllJointsValid()) {
      // Update parent with final numeric values before saving
      const numericJoints = localJoints.map(j => parseFloat(j.trim()));
      onUpdate(numericJoints);
      onSave();
      onClose();
    }
  };

  const handleCancel = () => {
    setLocalJoints(homeJoints.map(j => j.toString())); // Reset to original values as strings
    onUpdate(homeJoints);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="tactical-panel p-6 max-w-md w-full mx-4 relative">
        {/* Geometric overlay */}
        <div className="geometric-overlay absolute inset-0 rounded opacity-20"></div>
        
        {/* Scanning line effect */}
        <div className="scan-line"></div>
        
        <div className="relative z-10 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-tactical text-accent">Configure Home Joints</h2>
            <button 
              onClick={handleCancel}
              className="text-text-secondary hover:text-accent"
            >
              ✕
            </button>
          </div>

          <div className="space-y-3">
            <p className="text-sm text-text-secondary">
              Set home joint angles (in degrees). These will be converted to radians for the robot.
            </p>

            {/* Joint input fields */}
            <div className="grid grid-cols-2 gap-3">
              {localJoints.map((joint, index) => (
                <div key={index} className="space-y-1">
                  <label className="text-xs text-text-secondary">
                    Joint {index + 1}°
                  </label>
                  <Input
                    type="number"
                    value={joint}
                    onChange={(e) => handleJointChange(index, e.target.value)}
                    step="0.01"
                    className={`text-xs bg-surface-dark border-accent/30 text-text-primary ${
                      joint.trim() === '' || isNaN(parseFloat(joint.trim())) 
                        ? 'border-red-500/50 bg-red-900/20' 
                        : ''
                    }`}
                    placeholder={`J${index + 1}`}
                  />
                </div>
              ))}
            </div>

            {/* Current robot values display */}
            <div className="bg-surface-dark/50 p-3 rounded border border-accent/20">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs text-accent font-tactical">Current Robot Position (degrees):</h4>
                <button
                  onClick={fetchCurrentJoints}
                  disabled={loadingCurrentJoints}
                  className="text-xs px-2 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded border border-blue-500/30 transition-colors"
                >
                  {loadingCurrentJoints ? '🔄' : '🔄 Refresh'}
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                {loadingCurrentJoints ? (
                  <div className="col-span-3 text-center text-text-secondary">
                    Loading current position...
                  </div>
                ) : currentRobotJoints.length > 0 ? (
                  currentRobotJoints.map((joint, index) => (
                    <div key={index} className="text-text-secondary">
                      J{index + 1}: {joint.toFixed(2)}°
                    </div>
                  ))
                ) : (
                  <div className="col-span-3 text-center text-red-400">
                    Robot not connected or unable to read position
                  </div>
                )}
              </div>
            </div>

            {/* Home joint values display */}
            <div className="bg-surface-dark/50 p-3 rounded border border-accent/20">
              <h4 className="text-xs text-accent font-tactical mb-2">Home Joint Configuration (degrees):</h4>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                {localJoints.map((joint, index) => (
                  <div key={index} className="text-text-secondary">
                    J{index + 1}: {
                      joint.trim() === '' || isNaN(parseFloat(joint.trim())) 
                        ? '---' 
                        : parseFloat(joint.trim()).toFixed(2)
                    }°
                  </div>
                ))}
              </div>
            </div>

            {/* Validation message */}
            {!areAllJointsValid() && (
              <div className="bg-red-900/20 border border-red-500/30 p-2 rounded">
                <p className="text-xs text-red-400">
                  ❌ All joint fields must be filled with valid numbers to save.
                </p>
              </div>
            )}

            {/* Save current position button */}
            <div className="flex justify-center mb-3">
              <button 
                onClick={onSaveCurrentAsHome}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors border border-blue-500"
              >
                📍 Save Current as Home
              </button>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button 
                onClick={handleCancel}
                className="flex-1 py-2 px-4 border border-text-secondary/30 rounded text-text-secondary hover:border-text-secondary hover:text-text-primary transition-colors text-sm"
              >
                Cancel
              </button>
              <button 
                onClick={handleSave}
                disabled={!areAllJointsValid()}
                className={`flex-1 py-2 px-4 rounded text-sm transition-all ${
                  areAllJointsValid()
                    ? 'tactical-button cursor-pointer'
                    : 'bg-gray-600 text-gray-400 cursor-not-allowed border border-gray-500'
                }`}
              >
                Save & Apply
              </button>
            </div>

            {/* Safety note */}
            <div className="bg-warning/10 border border-warning/30 p-2 rounded">
              <p className="text-xs text-warning">
                ⚠️ Ensure joint angles are within safe operating limits before applying.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}