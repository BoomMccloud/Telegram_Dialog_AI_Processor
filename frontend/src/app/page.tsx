'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from './SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function Home() {
  const [qrCode, setQrCode] = useState<string>('');
  const [tempSessionId, setTempSessionId] = useState<string>('');
  const [authStatus, setAuthStatus] = useState<string>('pending');
  const [isLoading, setIsLoading] = useState(false);
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
      setTempSessionId(data.session_id);
      setAuthStatus('pending');
      login(data.session_id, 'pending');
    } catch (error) {
      console.error('Error creating QR session:', error);
      setAuthStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

  const checkSessionStatus = async () => {
    if (!tempSessionId) return;

    try {
      console.log('Checking session status for:', tempSessionId);
      const response = await fetch(`${API_URL}/auth/session/${tempSessionId}`);
      
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
        router.push('/home');
      }
    } catch (error) {
      console.error('Error checking session status:', error);
      // Don't set error status on network errors, just log and continue polling
    }
  };

  // Only create QR session on initial load or manual regeneration
  useEffect(() => {
    const shouldCreateSession = !qrCode && !isLoading && !tempSessionId;
    if (shouldCreateSession) {
      createQrSession();
    }
  }, []); // Empty dependency array, only run on mount

  // Only redirect if authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/home');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;
    
    if (tempSessionId && authStatus === 'pending') {
      intervalId = setInterval(checkSessionStatus, 2000);
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [tempSessionId, authStatus]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Telegram Dialog Processor
        </h1>
        
        <div className="bg-white rounded-lg p-8 shadow-lg max-w-md mx-auto dark:bg-gray-800">
          <h2 className="text-2xl font-semibold mb-4 text-center">
            Telegram Login
          </h2>
          
          {!qrCode && !isLoading && (
            <div className="flex flex-col items-center">
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                Click the button below to start the login process
              </p>
              <button
                onClick={createQrSession}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
              >
                Login with Telegram
              </button>
            </div>
          )}
          
          {isLoading && (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-gray-100"></div>
            </div>
          )}
          
          {qrCode && !isLoading && (
            <div className="flex flex-col items-center">
              <img
                src={qrCode}
                alt="QR Code"
                className="w-64 h-64 mb-4"
              />
              <p className="text-gray-600 dark:text-gray-300">
                Open Telegram and scan this QR code to log in
              </p>
              {authStatus === 'pending' && (
                <p className="text-blue-600 mt-2">
                  Waiting for authentication...
                </p>
              )}
              {authStatus === 'authenticated' && (
                <p className="text-green-600 mt-2">
                  Authentication successful!
                </p>
              )}
              {authStatus === 'error' && (
                <div className="flex flex-col items-center mt-4">
                  <p className="text-red-600 mb-2">
                    QR code expired. Please try again.
                  </p>
                  <button
                    onClick={createQrSession}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                  >
                    Generate New QR Code
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
