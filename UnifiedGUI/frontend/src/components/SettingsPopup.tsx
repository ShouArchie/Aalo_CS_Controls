import { useState } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsPopup({ isOpen, onClose }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-accent">Keyboard Shortcuts</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">Toggle Temperature Filter</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-accent">Alt + F</kbd>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Adjust Temperature Range</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-accent">Alt + T</kbd>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Cycle Color Palette</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-accent">Alt + P</kbd>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-300">Manual Calibration (FFC)</span>
            <kbd className="bg-gray-800 px-2 py-1 rounded text-accent">Alt + C</kbd>
          </div>
          
          <hr className="border-gray-700 my-4" />
          
          <div className="text-gray-400 text-xs">
            <p>• Click on thermal image to get temperature readings</p>
            <p>• Min/Max temperatures update automatically</p>
            <p>• Filter settings persist during session</p>
          </div>
        </div>
      </div>
    </div>
  );
}