import { useEffect, useRef, useState } from 'react';

export function useCameraStream(url: string) {
  const [fps, setFps] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let socket: WebSocket | null = new WebSocket(url.replace('http', 'ws'));
    let lastTime = performance.now();
    let frames = 0;
    let isProcessing = false;
    let lastFrameUrl: string | null = null;

    // frame queue for smooth playback
    const frameQueue: ArrayBuffer[] = [];
    const MAX_QUEUE_SIZE = 2; // keep only latest frames for low latency

    socket.binaryType = 'arraybuffer';

    const processFrame = () => {
      if (frameQueue.length > 0 && !isProcessing) {
        isProcessing = true;
        const frameData = frameQueue.shift()!;
        
        // clear old frames to reduce latency
        if (frameQueue.length > MAX_QUEUE_SIZE) {
          frameQueue.splice(0, frameQueue.length - 1);
        }
        
        const blob = new Blob([frameData], { type: 'image/jpeg' });
        const img = new Image();
        
        img.onload = () => {
          // resize canvas if needed
          if (canvas.width !== img.width || canvas.height !== img.height) {
            canvas.width = img.width;
            canvas.height = img.height;
          }
          
          // draw new frame
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
          
          // calc fps
          frames += 1;
          const now = performance.now();
          if (now - lastTime >= 1000) {
            setFps(frames);
            frames = 0;
            lastTime = now;
          }
          
          // cleanup old url
          if (lastFrameUrl) {
            URL.revokeObjectURL(lastFrameUrl);
          }
          lastFrameUrl = img.src;
          
          isProcessing = false;
          
          // process next frame if available
          if (frameQueue.length > 0) {
            requestAnimationFrame(processFrame);
          }
        };
        
        img.onerror = () => {
          if (lastFrameUrl) {
            URL.revokeObjectURL(lastFrameUrl);
          }
          isProcessing = false;
          // try next frame on error
          if (frameQueue.length > 0) {
            requestAnimationFrame(processFrame);
          }
        };
        
        img.src = URL.createObjectURL(blob);
      }
    };

    socket.onmessage = (ev) => {
      // add to queue and start processing
      frameQueue.push(ev.data);
      if (!isProcessing) {
        requestAnimationFrame(processFrame);
      }
    };

    socket.onopen = () => {
      console.log(`WebSocket connected: ${url}`);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
      console.log(`WebSocket closed: ${url}`);
    };

    return () => {
      socket?.close();
      // cleanup frame urls
      if (lastFrameUrl) {
        URL.revokeObjectURL(lastFrameUrl);
      }
      frameQueue.length = 0;
    };
  }, [url]);

  return { canvasRef, fps };
} 