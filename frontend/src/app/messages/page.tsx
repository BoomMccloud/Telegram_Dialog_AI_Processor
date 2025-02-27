'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface Dialog {
  id: number;
  name: string;
  unread_count: number;
  is_group: boolean;
  is_channel: boolean;
  is_user: boolean;
}

export default function MessagesPage() {
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  
  // Get session ID from localStorage
  const sessionId = typeof window !== 'undefined' ? localStorage.getItem('sessionId') : null;

  useEffect(() => {
    // Redirect to login if no session ID
    if (!sessionId) {
      router.push('/');
      return;
    }

    const fetchDialogs = async () => {
      try {
        const response = await fetch(`${API_URL}/dialogs/${sessionId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch dialogs');
        }
        const data = await response.json();
        setDialogs(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchDialogs();
    // Refresh dialogs every 30 seconds
    const interval = setInterval(fetchDialogs, 30000);
    return () => clearInterval(interval);
  }, [sessionId, router]);

  if (!sessionId) {
    return null; // Will redirect
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-red-500">Error: {error}</div>
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col p-8">
      <h1 className="text-3xl font-bold mb-6">Your Chats</h1>
      
      <div className="space-y-4">
        {dialogs.map((dialog) => (
          <div
            key={dialog.id}
            className="p-4 rounded-lg shadow bg-white hover:bg-gray-50 cursor-pointer"
          >
            <div className="flex justify-between items-center">
              <div>
                <h2 className="font-semibold text-lg">{dialog.name}</h2>
                <p className="text-sm text-gray-500">
                  {dialog.is_group ? 'Group' : dialog.is_channel ? 'Channel' : 'Direct Message'}
                </p>
              </div>
              {dialog.unread_count > 0 && (
                <span className="bg-blue-500 text-white px-2 py-1 rounded-full text-sm">
                  {dialog.unread_count}
                </span>
              )}
            </div>
          </div>
        ))}
        
        {dialogs.length === 0 && (
          <div className="text-center text-gray-500">
            No chats found
          </div>
        )}
      </div>
    </main>
  );
} 