'use client';

import { useState, useEffect } from 'react';
import { getSessionId, setSessionId, clearSessionId, isDevelopmentMode } from '../utils/sessionManager';

/**
 * DevTools component for development purposes
 * Only shows in development mode and provides utilities for testing
 */
export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [sessionId, setSessionIdState] = useState<string>('');
  const [mockSessionId, setMockSessionId] = useState<string>('');
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Only show in development mode
    setIsVisible(isDevelopmentMode());

    // Get current session ID from localStorage
    const storedSessionId = getSessionId();
    if (storedSessionId) {
      setSessionIdState(storedSessionId);
    }
  }, []);

  if (!isVisible) return null;

  const handleSetMockSession = () => {
    if (mockSessionId) {
      setSessionId(mockSessionId);
      setSessionIdState(mockSessionId);
      alert('Session ID set! Reload the page if needed.');
    } else {
      alert('Please enter a session ID');
    }
  };

  const handleClearSession = () => {
    clearSessionId();
    setSessionIdState('');
    alert('Session cleared! Reload the page if needed.');
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
      .then(() => alert('Copied to clipboard!'))
      .catch(err => console.error('Failed to copy:', err));
  };

  const testApiConnection = async () => {
    if (!sessionId) {
      alert('No session ID set');
      return;
    }
    
    try {
      const response = await fetch(`/api/dialogs/${sessionId}`);
      const data = await response.json();
      
      if (response.ok) {
        alert(`Connection successful! Found ${data.length} dialogs.`);
      } else {
        alert(`API Error: ${data.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Connection failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div 
      className="fixed bottom-4 right-4 z-50 bg-gray-800 text-white rounded-lg shadow-lg overflow-hidden"
      style={{ maxWidth: isExpanded ? '400px' : '48px', transition: 'max-width 0.3s ease' }}
    >
      {/* Toggle button */}
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-12 h-12 flex items-center justify-center bg-orange-600 hover:bg-orange-700"
      >
        {isExpanded ? '✕' : '🛠️'}
      </button>

      {/* Expanded panel */}
      {isExpanded && (
        <div className="p-4">
          <h3 className="text-lg font-semibold mb-3">Development Tools</h3>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Current Session ID:</label>
            <div className="flex items-center">
              <input 
                type="text" 
                value={sessionId} 
                readOnly 
                className="flex-1 bg-gray-700 text-white px-2 py-1 rounded text-sm font-mono"
              />
              {sessionId && (
                <button 
                  onClick={() => copyToClipboard(sessionId)}
                  className="ml-2 bg-blue-500 hover:bg-blue-600 text-xs px-2 py-1 rounded"
                >
                  Copy
                </button>
              )}
            </div>
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Set Mock Session ID:</label>
            <div className="flex items-center">
              <input 
                type="text" 
                value={mockSessionId}
                onChange={(e) => setMockSessionId(e.target.value)}
                placeholder="Paste session ID from backend"
                className="flex-1 bg-gray-700 text-white px-2 py-1 rounded text-sm font-mono"
              />
            </div>
          </div>
          
          <div className="flex space-x-2 mb-4">
            <button 
              onClick={handleSetMockSession}
              className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
            >
              Set Session
            </button>
            <button 
              onClick={handleClearSession}
              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm"
            >
              Clear Session
            </button>
          </div>

          {sessionId && (
            <button 
              onClick={testApiConnection}
              className="w-full bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded text-sm mb-4"
            >
              Test API Connection
            </button>
          )}

          <div className="mt-4 pt-3 border-t border-gray-600">
            <p className="text-xs text-gray-400">
              To get a mock session ID, run:
              <br />
              <code className="block bg-gray-700 p-1 rounded mt-1 text-xs font-mono">
                cat backend/app/dev_utils/mock_session.txt
              </code>
            </p>
          </div>
        </div>
      )}
    </div>
  );
} 