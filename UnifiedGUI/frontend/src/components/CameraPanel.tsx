import { useCameraStream } from '@components/useCameraStream';
import { useState, useCallback, useEffect } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

interface Props {
  title: string;
  wsUrl: string;
  isThermal?: boolean;
  filterEnabled?: boolean;
  tempRange?: { min: number; max: number };
  colorPalette?: string;
}

interface TempData {
  temperature?: number;
  min_temp?: number;
  max_temp?: number;
  temp_range?: number;
  x?: number;
  y?: number;
}

export default function CameraPanel({ 
  title, 
  wsUrl, 
  isThermal = false, 
  filterEnabled = false, 
  tempRange = { min: 0, max: 50 }, 
  colorPalette = 'PLASMA' 
}: Props) {
  const { canvasRef, fps } = useCameraStream(wsUrl);
  const [tempData, setTempData] = useState<TempData>({});

  const handleCanvasClick = useCallback(async (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isThermal || !canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    
    // Calculate the actual image dimensions within the canvas (accounting for object-fit: contain)
    const imageAspectRatio = canvas.width / canvas.height;
    const canvasAspectRatio = rect.width / rect.height;
    
    let imageDisplayWidth, imageDisplayHeight, offsetX, offsetY;
    
    if (imageAspectRatio > canvasAspectRatio) {
      // Image is wider - letterboxed top/bottom
      imageDisplayWidth = rect.width;
      imageDisplayHeight = rect.width / imageAspectRatio;
      offsetX = 0;
      offsetY = (rect.height - imageDisplayHeight) / 2;
    } else {
      // Image is taller - letterboxed left/right
      imageDisplayWidth = rect.height * imageAspectRatio;
      imageDisplayHeight = rect.height;
      offsetX = (rect.width - imageDisplayWidth) / 2;
      offsetY = 0;
    }
    
    // Calculate click position relative to the actual image
    const clickX = event.clientX - rect.left - offsetX;
    const clickY = event.clientY - rect.top - offsetY;
    
    // Convert to image coordinates
    const displayX = Math.floor((clickX / imageDisplayWidth) * canvas.width);
    const displayY = Math.floor((clickY / imageDisplayHeight) * canvas.height);
    
    // Only process clicks within the image bounds
    if (displayX < 0 || displayX >= canvas.width || displayY < 0 || displayY >= canvas.height) return;
    
    // Account for 180-degree rotation applied in backend
    // The displayed image is rotated, so we need to transform coordinates back to original orientation
    const x = canvas.width - displayX - 1;
    const y = canvas.height - displayY - 1;
    
    try {
              const response = await fetch(API_ENDPOINTS.TEMPERATURE_AT(x, y));
      const data = await response.json();
      if (data.temperature) {
        setTempData(prev => ({ ...prev, temperature: data.temperature, x, y }));
      }
    } catch (error) {
      console.error('Failed to get temperature:', error);
    }
  }, [isThermal, canvasRef]);

  // Fetch min/max data periodically for thermal camera
  useEffect(() => {
    if (!isThermal) return;
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(API_ENDPOINTS.THERMAL_MINMAX);
        const data = await response.json();
        if (data.min_temp !== undefined) {
          setTempData(prev => ({ ...prev, ...data }));
        }
      } catch (error) {
        console.error('Failed to get min/max data:', error);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [isThermal]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className={`status-indicator ${isThermal ? 'bg-warning' : 'bg-success'}`}></div>
          <h2 className="text-sm font-tactical font-bold text-accent uppercase tracking-wider">
            {title}
          </h2>
        </div>
        <div className="text-xs font-mono text-text-secondary">
          {fps} FPS
        </div>
      </div>

      {/* Camera Display - Takes remaining space */}
      <div className="relative bg-surface-dark rounded overflow-hidden flex-1">
        <canvas 
          ref={canvasRef} 
          className={`w-full h-full ${isThermal ? 'cursor-crosshair' : ''} block`}
          onClick={handleCanvasClick}
          style={{ objectFit: 'contain' }}
        />
        


        {/* Temperature Data Overlay */}
        {isThermal && (
          <div className="absolute top-3 left-3 bg-white bg-opacity-90 border border-gray-300 rounded p-2 space-y-1 text-xs font-mono backdrop-blur-sm">
            {tempData.min_temp !== undefined && (
              <div className="text-black">
                <span className="text-blue-600 font-bold">MIN:</span> {tempData.min_temp}°C | 
                <span className="text-red-600 font-bold ml-1">MAX:</span> {tempData.max_temp}°C
              </div>
            )}
            {tempData.temperature && (
              <div className="text-black font-bold">
                POINT [{tempData.x},{tempData.y}]: {tempData.temperature}°C
              </div>
            )}
          </div>
        )}

        {/* Status Indicators */}
        <div className="absolute bottom-3 right-3 flex gap-2">
          {isThermal && (
            <>
              <div className={`px-2 py-1 rounded text-xs font-mono ${
                filterEnabled 
                  ? 'bg-success bg-opacity-20 text-success border border-success' 
                  : 'bg-warning bg-opacity-20 text-warning border border-warning'
              }`}>
                {filterEnabled ? 'FILT' : 'RAW'}
              </div>
              <div className="px-2 py-1 rounded text-xs font-mono bg-accent bg-opacity-20 text-accent border border-accent">
                {colorPalette}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Technical Readout */}
      {isThermal && filterEnabled && (
        <div className="text-xs font-mono text-text-secondary">
          FILTER RANGE: {tempRange.min}°C → {tempRange.max}°C
        </div>
      )}
    </div>
  );
} 