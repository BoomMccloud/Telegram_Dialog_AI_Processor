'use client';

import { useState, useEffect } from 'react';
import { useSession } from '../SessionContext';
import Image from 'next/image';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [qrCode, setQrCode] = useState<string>('');
  const [isGeneratingQR, setIsGeneratingQR] = useState(false);
  const [telegramId, setTelegramId] = useState('');
  const { session, login, logout } = useSession();
  
  // Only show in development mode
  useEffect(() => {
    setIsVisible(process.env.NODE_ENV === 'development');
  }, []);

  if (!isVisible) {
    return null;
  }

  const generateQRCode = async () => {
    setIsGeneratingQR(true);
    try {
      const response = await fetch(`${API_URL}/auth/qr`, {
        method: 'POST',
      });
      const data = await response.json();
      setQrCode(data.qr_code);
      login(data.token, 'pending');
    } catch (error) {
      console.error('Error generating QR code:', error);
      alert('Failed to generate QR code');
    } finally {
      setIsGeneratingQR(false);
    }
  };

  const handleDevLogin = async () => {
    if (!telegramId) {
      alert('Please enter a Telegram ID');
      return;
    }

    try {
      // Call the development-only login endpoint
      const response = await fetch(`${API_URL}/auth/dev-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ telegram_id: parseInt(telegramId, 10) })
      });

      if (!response.ok) {
        throw new Error('Login failed: ' + await response.text());
      }

      const data = await response.json();
      login(data.token, 'authenticated');
      setQrCode('');
      alert('Development login successful!');
    } catch (error) {
      console.error('Login error:', error);
      alert(error instanceof Error ? error.message : 'Login failed');
    }
  };

  const clearSession = () => {
    logout();
    setQrCode('');
  };

  const copyToClipboard = () => {
    if (session?.token) {
      navigator.clipboard.writeText(session.token);
      alert('JWT token copied to clipboard!');
    }
  };

  return (
    <div className="fixed bottom-4 right-4 p-4 bg-gray-800 text-white rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-4">Development Tools</h3>
      
      <div className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm">Quick Development Login:</p>
          <input
            type="number"
            value={telegramId}
            onChange={(e) => setTelegramId(e.target.value)}
            placeholder="Enter Telegram ID"
            className="w-full p-2 text-black rounded"
          />
          <button
            onClick={handleDevLogin}
            className="w-full px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
            disabled={!telegramId}
          >
            Dev Login
          </button>
        </div>

        <div className="border-t border-gray-600 my-4"></div>

        {qrCode ? (
          <div className="space-y-2">
            <p className="text-sm">QR Code Authentication:</p>
            <div className="bg-white p-2 rounded">
              <Image
                src={`data:image/png;base64,${qrCode}`}
                alt="QR Code"
                width={200}
                height={200}
                className="mx-auto"
              />
            </div>
          </div>
        ) : (
          <button
            onClick={generateQRCode}
            className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            disabled={isGeneratingQR}
          >
            {isGeneratingQR ? 'Generating QR...' : 'Generate QR Code'}
          </button>
        )}

        <div className="space-y-2">
          <button
            onClick={clearSession}
            className="w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Clear Session
          </button>
          
          <button
            onClick={copyToClipboard}
            className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            disabled={!session?.token}
          >
            Copy JWT Token
          </button>
        </div>

        <div className="mt-4 text-sm">
          <p>Current Token:</p>
          <pre className="mt-1 p-2 bg-gray-700 rounded overflow-x-auto max-w-[300px] break-all">
            {session?.token || 'No token'}
          </pre>
        </div>
      </div>
    </div>
  );
}

