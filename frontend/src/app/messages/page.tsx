'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '../ThemeContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface Dialog {
  id: number;
  name: string;
  unread_count: number;
  is_group: boolean;
  is_channel: boolean;
  is_user: boolean;
}

type TabType = 'groups' | 'channels' | 'direct';

interface DialogListProps {
  dialogs: Dialog[];
}

const DialogList: React.FC<DialogListProps> = ({ dialogs }) => {
  if (dialogs.length === 0) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-4">
        No chats found
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {dialogs.map((dialog) => (
        <div
          key={dialog.id}
          className="p-4 rounded-lg shadow bg-white dark:bg-gray-800 
            hover:bg-gray-50 dark:hover:bg-gray-700 
            cursor-pointer transition-colors border border-gray-200 dark:border-gray-700
            flex justify-between items-center"
        >
          <h2 className="font-semibold text-lg dark:text-white truncate pr-4">
            {dialog.name}
          </h2>
          <div className={`
            flex items-center whitespace-nowrap px-3 py-1 rounded-full text-sm
            ${dialog.unread_count > 0
              ? 'bg-blue-500 dark:bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}
          >
            <span className="font-medium">{dialog.unread_count || '0'}</span>
            <span className="ml-1 font-normal">messages unread</span>
          </div>
        </div>
      ))}
    </div>
  );
};

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <button
      onClick={toggleTheme}
      className="fixed top-4 right-4 p-2 rounded-lg bg-gray-200 dark:bg-gray-700 
        hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'light' ? (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      ) : (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707" />
        </svg>
      )}
    </button>
  );
};

export default function MessagesPage() {
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('direct');
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
      <div className="flex min-h-screen items-center justify-center dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center dark:bg-gray-900">
        <div className="text-red-500 dark:text-red-400">Error: {error}</div>
      </div>
    );
  }

  const filteredDialogs = {
    groups: dialogs.filter(d => d.is_group),
    channels: dialogs.filter(d => d.is_channel),
    direct: dialogs.filter(d => d.is_user)
  };

  const totalUnread = {
    groups: filteredDialogs.groups.reduce((sum, d) => sum + d.unread_count, 0),
    channels: filteredDialogs.channels.reduce((sum, d) => sum + d.unread_count, 0),
    direct: filteredDialogs.direct.reduce((sum, d) => sum + d.unread_count, 0)
  };

  return (
    <main className="flex min-h-screen flex-col p-8 bg-gray-50 dark:bg-gray-900">
      <ThemeToggle />
      
      <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">
        Your Chats
      </h1>
      
      <div className="mb-6">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {[
              { id: 'direct', name: 'Direct Messages', count: totalUnread.direct },
              { id: 'groups', name: 'Groups', count: totalUnread.groups },
              { id: 'channels', name: 'Channels', count: totalUnread.channels },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`
                  whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
                  }
                `}
              >
                {tab.name}
                {tab.count > 0 && (
                  <span className={`
                    ml-2 py-0.5 px-2 rounded-full text-xs
                    ${activeTab === tab.id 
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400' 
                      : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-300'}
                  `}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="mt-4">
        <DialogList dialogs={filteredDialogs[activeTab]} />
      </div>
    </main>
  );
} 