'use client';

import { useState, useEffect } from 'react';
import { useSession } from '../SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [telegramId, setTelegramId] = useState('');
  const { login } = useSession();
  
  // Only show in development mode
  useEffect(() => {
    setIsVisible(process.env.NODE_ENV === 'development');
  }, []);

  if (!isVisible) {
    return null;
  }

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
        const errorText = await response.text();
        console.error('Login failed:', errorText);
        throw new Error('Login failed: ' + errorText);
      }

      const data = await response.json();
      console.log('Login response:', data);
      
      // Store the token and session ID with authenticated status
      login(data.token, data.session_id, 'authenticated');
      alert('Development login successful!');
    } catch (error) {
      console.error('Login error:', error);
      alert(error instanceof Error ? error.message : 'Login failed');
    }
  };

  return (
    <div className="fixed bottom-4 right-4 p-4 bg-gray-800 text-white rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-4">Dev Login</h3>
      
      <div className="space-y-4">
        <div className="space-y-2">
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
            Login with Telegram ID
          </button>
        </div>
      </div>
    </div>
  );
}

