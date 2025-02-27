'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function Home() {
  const [qrCode, setQrCode] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');
  const [status, setStatus] = useState<string>('pending');
  const router = useRouter();

  const createQrSession = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/qr`, {
        method: 'POST',
      });
      const data = await response.json();
      setQrCode(data.qr_code);
      setSessionId(data.session_id);
    } catch (error) {
      console.error('Error creating QR session:', error);
    }
  };

  const checkSessionStatus = async () => {
    if (!sessionId) return;

    try {
      console.log('Checking session status for:', sessionId);
      const response = await fetch(`${API_URL}/auth/session/${sessionId}`);
      const data = await response.json();
      console.log('Session status response:', data);
      setStatus(data.status);

      if (data.status === 'authenticated') {
        console.log('Authentication successful, storing session and redirecting...');
        localStorage.setItem('sessionId', sessionId);
        router.push('/messages');
      }
    } catch (error) {
      console.error('Error checking session status:', error);
    }
  };

  useEffect(() => {
    // Check if already authenticated
    const storedSessionId = localStorage.getItem('sessionId');
    if (storedSessionId) {
      router.push('/messages');
      return;
    }

    createQrSession();
  }, [router]);

  useEffect(() => {
    if (sessionId && status === 'pending') {
      const interval = setInterval(checkSessionStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [sessionId, status]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">
          Telegram Dialog Processor
        </h1>
        
        <div className="bg-white rounded-lg p-8 shadow-lg max-w-md mx-auto">
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
              <p className="text-gray-600">
                Open Telegram and scan this QR code to log in
              </p>
              {status === 'pending' && (
                <p className="text-blue-600 mt-2">
                  Waiting for authentication...
                </p>
              )}
              {status === 'authenticated' && (
                <p className="text-green-600 mt-2">
                  Authentication successful!
                </p>
              )}
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
