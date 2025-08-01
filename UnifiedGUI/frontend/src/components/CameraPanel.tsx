import { useCameraStream } from '@components/useCameraStream';
import { useState, useCallback, useEffect } from 'react';

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
    const x = Math.floor((event.clientX - rect.left) * (canvas.width / rect.width));
    const y = Math.floor((event.clientY - rect.top) * (canvas.height / rect.height));
    
    try {
      const response = await fetch(`http://localhost:8000/api/temperature/${x}/${y}`);
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
        const response = await fetch('http://localhost:8000/api/thermal/minmax');
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
    <div className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold text-accent drop-shadow-glow">{title}</h2>
      <div className="relative">
        <canvas 
          ref={canvasRef} 
          className={`border border-gray-700 rounded w-full h-auto ${isThermal ? 'cursor-crosshair' : ''}`}
          onClick={handleCanvasClick}
          style={{ aspectRatio: '4/3' }}
        />
        {isThermal && (
          <div className="absolute top-2 left-2 bg-black bg-opacity-70 text-white text-xs p-2 rounded space-y-1">
            {tempData.min_temp !== undefined && (
              <div>Min: {tempData.min_temp}°C | Max: {tempData.max_temp}°C</div>
            )}
            {tempData.temperature && (
              <div>Point ({tempData.x}, {tempData.y}): {tempData.temperature}°C</div>
            )}
          </div>
        )}
      </div>
      
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-400">FPS: {fps}</span>
        {isThermal && (
          <div className="flex gap-4 text-xs">
            <span className={`font-medium ${filterEnabled ? 'text-green-400' : 'text-orange-400'}`}>
              Filter: {filterEnabled ? 'ON' : 'OFF'}
            </span>
            {filterEnabled && (
              <span className="text-gray-400">
                {tempRange.min}°C - {tempRange.max}°C
              </span>
            )}
            <span className="text-accent">{colorPalette}</span>
          </div>
        )}
      </div>
    </div>
  );
} 