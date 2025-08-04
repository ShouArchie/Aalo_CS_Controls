"use client";
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to main dashboard by default
    router.push('/main');
  }, [router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-surface-dark">
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-tactical text-accent">UR10e Control System</h1>
        <p className="text-text-secondary">Redirecting to main dashboard...</p>
        
        {/* Navigation Links */}
        <div className="flex gap-4 mt-8">
            <button 
            onClick={() => router.push('/main')}
            className="tactical-button px-6 py-3 rounded"
            >
            Main Dashboard
            </button>
            <button
            onClick={() => router.push('/views')}
            className="tactical-button px-6 py-3 rounded"
          >
            Camera Views
                      </button>
                      <button 
            onClick={() => router.push('/controls')}
            className="tactical-button px-6 py-3 rounded"
          >
            Robot Controls
                    </button>
        </div>
      </div>
    </main>
  );
} 