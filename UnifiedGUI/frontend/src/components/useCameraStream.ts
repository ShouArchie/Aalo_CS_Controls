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

    socket.binaryType = 'arraybuffer';

    socket.onmessage = (ev) => {
      const blob = new Blob([ev.data], { type: 'image/jpeg' });
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        frames += 1;
        const now = performance.now();
        if (now - lastTime >= 1000) {
          setFps(frames);
          frames = 0;
          lastTime = now;
        }
      };
      img.src = URL.createObjectURL(blob);
    };

    return () => {
      socket?.close();
    };
  }, [url]);

  return { canvasRef, fps };
} 