import { useState } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsPopup({ isOpen, onClose }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="tactical-panel p-6 max-w-lg w-full mx-4 rounded-lg relative corner-brackets">
        <div className="geometric-overlay">
          <div className="scan-line"></div>
        </div>
        
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2">
            <div className="status-indicator bg-accent"></div>
            <h3 className="text-lg font-tactical font-bold text-accent uppercase tracking-wider">
              System Configuration
            </h3>
          </div>
          <button
            onClick={onClose}
            className="tactical-button px-3 py-1 rounded text-xs"
          >
            CLOSE
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-tactical text-accent uppercase tracking-wider mb-3">
              Keyboard Commands
            </h4>
            <div className="space-y-2 text-sm font-mono">
              <div className="flex justify-between items-center p-2 bg-surface-medium rounded">
                <span className="text-text-secondary">Toggle Temperature Filter</span>
                <kbd className="bg-surface-dark border border-border-primary px-2 py-1 rounded text-accent text-xs">
                  ALT + F
                </kbd>
              </div>
              
              <div className="flex justify-between items-center p-2 bg-surface-medium rounded">
                <span className="text-text-secondary">Adjust Temperature Range</span>
                <kbd className="bg-surface-dark border border-border-primary px-2 py-1 rounded text-accent text-xs">
                  ALT + T
                </kbd>
              </div>
              
              <div className="flex justify-between items-center p-2 bg-surface-medium rounded">
                <span className="text-text-secondary">Cycle Color Palette</span>
                <kbd className="bg-surface-dark border border-border-primary px-2 py-1 rounded text-accent text-xs">
                  ALT + P
                </kbd>
              </div>
              
              <div className="flex justify-between items-center p-2 bg-surface-medium rounded">
                <span className="text-text-secondary">Manual Calibration (FFC)</span>
                <kbd className="bg-surface-dark border border-border-primary px-2 py-1 rounded text-accent text-xs">
                  ALT + C
                </kbd>
              </div>
              
              <div className="flex justify-between items-center p-2 bg-surface-medium rounded">
                <span className="text-text-secondary">Open Settings Panel</span>
                <kbd className="bg-surface-dark border border-border-primary px-2 py-1 rounded text-accent text-xs">
                  F1
                </kbd>
              </div>
            </div>
          </div>
          
          <div className="border-t border-border-primary pt-4">
            <h4 className="text-sm font-tactical text-accent uppercase tracking-wider mb-3">
              Operation Notes
            </h4>
            <div className="text-text-tertiary text-xs font-mono space-y-1">
              <p>• THERMAL.SENSOR: Click for temperature readings</p>
              <p>• DATA.REFRESH: Min/Max values update automatically</p>
              <p>• CONFIG.PERSIST: Filter settings maintained during session</p>
              <p>• SYS.STATUS: All functions operational</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}