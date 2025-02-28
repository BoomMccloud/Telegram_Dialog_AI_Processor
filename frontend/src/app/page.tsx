'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from './SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function Home() {
  const [qrCode, setQrCode] = useState<string>('');
  const [tempSessionId, setTempSessionId] = useState<string>('');
  const [authStatus, setAuthStatus] = useState<string>('pending');
  const router = useRouter();
  const { login, isAuthenticated } = useSession();

  const createQrSession = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/qr`, {
        method: 'POST',
      });
      const data = await response.json();
      setQrCode(data.qr_code);
      setTempSessionId(data.session_id);
    } catch (error) {
      console.error('Error creating QR session:', error);
    }
  };

  const checkSessionStatus = async () => {
    if (!tempSessionId) return;

    try {
      console.log('Checking session status for:', tempSessionId);
      const response = await fetch(`${API_URL}/auth/session/${tempSessionId}`);
      const data = await response.json();
      console.log('Session status response:', data);
      setAuthStatus(data.status);

      if (data.status === 'authenticated') {
        console.log('Authentication successful, storing session and redirecting...');
        login(tempSessionId);
        router.push('/home');
      }
    } catch (error) {
      console.error('Error checking session status:', error);
    }
  };

  useEffect(() => {
    // Check if already authenticated
    if (isAuthenticated) {
      router.push('/home');
      return;
    }

    createQrSession();
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (tempSessionId && authStatus === 'pending') {
      const interval = setInterval(checkSessionStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [tempSessionId, authStatus]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Telegram Dialog Processor
        </h1>
        
        <div className="bg-white rounded-lg p-8 shadow-lg max-w-md mx-auto dark:bg-gray-800">
          <h2 className="text-2xl font-semibold mb-4 text-center">
            Scan QR Code to Login
          </h2>
          
          {qrCode ? (
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
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-gray-100"></div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
