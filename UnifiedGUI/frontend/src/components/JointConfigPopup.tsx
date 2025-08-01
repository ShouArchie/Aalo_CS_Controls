'use client';

import { useState } from 'react';
import { Input } from '@/components/ui/input';

interface JointConfigPopupProps {
  isOpen: boolean;
  onClose: () => void;
  homeJoints: number[];
  onUpdate: (joints: number[]) => void;
  onSave: () => void;
}

export default function JointConfigPopup({ 
  isOpen, 
  onClose, 
  homeJoints, 
  onUpdate, 
  onSave 
}: JointConfigPopupProps) {
  const [localJoints, setLocalJoints] = useState(homeJoints);

  if (!isOpen) return null;

  const handleJointChange = (index: number, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      const newJoints = [...localJoints];
      newJoints[index] = numValue;
      setLocalJoints(newJoints);
      onUpdate(newJoints);
    }
  };

  const handleSave = () => {
    onSave();
  };

  const handleCancel = () => {
    setLocalJoints(homeJoints); // Reset to original values
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
                    value={joint.toFixed(2)}
                    onChange={(e) => handleJointChange(index, e.target.value)}
                    step="0.01"
                    className="text-xs bg-surface-dark border-accent/30 text-text-primary"
                    placeholder={`J${index + 1}`}
                  />
                </div>
              ))}
            </div>

            {/* Current values display */}
            <div className="bg-surface-dark/50 p-3 rounded border border-accent/20">
              <h4 className="text-xs text-accent font-tactical mb-2">Current Values (degrees):</h4>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                {localJoints.map((joint, index) => (
                  <div key={index} className="text-text-secondary">
                    J{index + 1}: {joint.toFixed(2)}°
                  </div>
                ))}
              </div>
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
                className="flex-1 tactical-button py-2 px-4 rounded text-sm"
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