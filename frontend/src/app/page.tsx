'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from './SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [qrCode, setQrCode] = useState<string>('');
  const [token, setToken] = useState<string>('');
  const [authStatus, setAuthStatus] = useState<string>('pending');
  const [isLoading, setIsLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<number>(Date.now());
  const router = useRouter();
  const { login, isAuthenticated } = useSession();

  const createQrSession = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/qr`, {
        method: 'POST',
      });
      const data = await response.json();
      setQrCode(data.qr_code);
      setToken(data.token);
      setAuthStatus('pending');
      setLastRefresh(Date.now());
      login(data.token, data.session_id, 'pending');
    } catch (error) {
      console.error('Error creating QR session:', error);
      setAuthStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

  const checkSessionStatus = async () => {
    if (!token) return;

    try {
      console.log('Checking session status...');
      const response = await fetch(`${API_URL}/auth/session/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      // Handle 401 (Unauthorized)
      if (response.status === 401) {
        const errorData = await response.json();
        // Only refresh QR code if the session is actually expired
        if (errorData.detail === "Session expired") {
          console.log('Session expired, refreshing QR code...');
          await createQrSession();
        }
        return;
      }
      
      // Only handle 404 as a true "not found" error
      if (response.status === 404) {
        console.log('Session not found');
        setAuthStatus('error');
        return;
      }
      
      // For all other non-200 responses, just log and continue polling
      if (!response.ok) {
        console.log('Non-200 response:', response.status);
        return;
      }
      
      const data = await response.json();
      console.log('Session status response:', data);
      
      // Only update status if it's different and valid
      if (data.status && data.status !== authStatus) {
        setAuthStatus(data.status);
      }

      if (data.status === 'authenticated') {
        console.log('Authentication successful, storing session and redirecting...');
        // If we get a new token in the response, use that instead
        const finalToken = data.token || token;
        login(finalToken, data.session_id, 'authenticated');
        router.push('/home');
      }
    } catch (error) {
      console.error('Error checking session status:', error);
      // Don't set error status on network errors, just log and continue polling
    }
  };

  // Create QR session on initial load or when needed
  useEffect(() => {
    const shouldCreateSession = !qrCode && !isLoading && !token;
    if (shouldCreateSession) {
      createQrSession();
    }
  }, [qrCode, isLoading, token]); // Add dependencies to re-run when needed

  // Refresh QR code every 9 minutes (before the 10-minute expiration)
  useEffect(() => {
    const refreshInterval = 9 * 60 * 1000; // 9 minutes in milliseconds
    const timeoutId = setTimeout(() => {
      if (authStatus === 'pending') {
        console.log('QR code about to expire, refreshing...');
        createQrSession();
      }
    }, refreshInterval);

    return () => clearTimeout(timeoutId);
  }, [lastRefresh, authStatus]);

  // Only redirect if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/home');
    }
  }, [isAuthenticated, router]);

  // Poll for session status
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;
    
    if (token && authStatus === 'pending') {
      intervalId = setInterval(checkSessionStatus, 2000);
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [token, authStatus]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <div className="flex flex-col items-center justify-center">
          <h1 className="text-4xl font-bold mb-8">Telegram Dialog AI Processor</h1>
          
          {isLoading ? (
            <div className="text-center">
              <p>Loading QR code...</p>
            </div>
          ) : qrCode ? (
            <div className="text-center">
              <img 
                src={`data:image/png;base64,${qrCode}`} 
                alt="QR Code for Telegram Login" 
                className="mb-4"
              />
              <p className="mb-2">Scan this QR code with your Telegram mobile app</p>
              <p className="text-sm text-gray-500">
                Status: {authStatus === 'pending' ? 'Waiting for scan...' : authStatus}
              </p>
              <button
                onClick={createQrSession}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Generate New QR Code
              </button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-red-500">Error loading QR code</p>
              <button
                onClick={createQrSession}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
