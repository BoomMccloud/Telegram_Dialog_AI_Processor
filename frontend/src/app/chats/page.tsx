'use client';

import { useEffect, useState } from 'react';
import AppLayout from '../AppLayout';

// Define types for the chat interface
interface Message {
  id: string;
  chatId: number;
  content: string;
  sender: {
    id: string;
    name: string;
  };
  timestamp: string;
  isFromUser: boolean;
}

interface GeneratedResponse {
  id: string;
  messageId: string;
  content: string;
  status: 'pending' | 'approved' | 'denied';
  timestamp: string;
  confidence: number;
}

interface ChatDialog {
  id: number;
  name: string;
  lastMessage?: string;
  unreadCount: number;
  isActive: boolean;
}

export default function ChatsPage() {
  const [selectedTab, setSelectedTab] = useState<'pending' | 'approved' | 'denied' | 'all'>('pending');
  const [loading, setLoading] = useState(true);
  const [selectedChat, setSelectedChat] = useState<number | null>(null);
  const [chats, setChats] = useState<ChatDialog[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [responses, setResponses] = useState<GeneratedResponse[]>([]);

  // Placeholder for fetching chat data
  useEffect(() => {
    // This would be replaced with actual API calls
    const fetchData = async () => {
      try {
        // Simulate API call with timeout
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock data for demo
        const mockChats: ChatDialog[] = [
          { id: 1, name: 'John Doe', lastMessage: 'Hello, how are you?', unreadCount: 2, isActive: true },
          { id: 2, name: 'Tech Support Group', lastMessage: 'Issue has been resolved', unreadCount: 0, isActive: true },
          { id: 3, name: 'Team Announcements', lastMessage: 'New project starting next week', unreadCount: 1, isActive: false }
        ];
        
        const mockMessages: Message[] = [
          {
            id: 'm1',
            chatId: 1,
            content: 'Hello, I have a question about the new product features.',
            sender: { id: 'u1', name: 'John Doe' },
            timestamp: '2023-10-15T14:30:00Z',
            isFromUser: true
          },
          {
            id: 'm2',
            chatId: 1,
            content: 'I heard there are new AI capabilities. Can you tell me more?',
            sender: { id: 'u1', name: 'John Doe' },
            timestamp: '2023-10-15T14:31:00Z',
            isFromUser: true
          }
        ];
        
        const mockResponses: GeneratedResponse[] = [
          {
            id: 'r1',
            messageId: 'm1',
            content: 'Yes, we have recently added several new features to our product suite. These include enhanced reporting, AI-powered analytics, and improved user interface.',
            status: 'pending',
            timestamp: '2023-10-15T14:32:00Z',
            confidence: 0.89
          },
          {
            id: 'r2',
            messageId: 'm2',
            content: 'Our new AI capabilities include natural language processing for better understanding of user queries, predictive analytics to anticipate user needs, and automated responses for common questions.',
            status: 'pending',
            timestamp: '2023-10-15T14:33:00Z',
            confidence: 0.92
          }
        ];
        
        setChats(mockChats);
        setMessages(mockMessages);
        setResponses(mockResponses);
        
        // Default to selecting the first chat
        if (mockChats.length > 0) {
          setSelectedChat(mockChats[0].id);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Handle response approval
  const handleApproveResponse = (responseId: string) => {
    setResponses(prev => 
      prev.map(response => 
        response.id === responseId 
          ? { ...response, status: 'approved' } 
          : response
      )
    );
  };

  // Handle response denial
  const handleDenyResponse = (responseId: string) => {
    setResponses(prev => 
      prev.map(response => 
        response.id === responseId 
          ? { ...response, status: 'denied' } 
          : response
      )
    );
  };

  // Get filtered messages for the selected chat
  const selectedChatMessages = messages.filter(message => 
    selectedChat && message.chatId === selectedChat
  );

  return (
    <AppLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Chats & Responses</h1>
          
          {loading ? (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
            </div>
          ) : (
            <div className="flex flex-col md:flex-row gap-6">
              {/* Sidebar with chat list */}
              <div className="w-full md:w-64 bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-medium text-gray-900 dark:text-white">Active Chats</h2>
                </div>
                <div className="overflow-y-auto max-h-[calc(100vh-250px)]">
                  {chats.map(chat => (
                    <div
                      key={chat.id}
                      className={`p-4 border-b border-gray-200 dark:border-gray-700 cursor-pointer
                        ${selectedChat === chat.id ? 'bg-blue-50 dark:bg-gray-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                      onClick={() => setSelectedChat(chat.id)}
                    >
                      <div className="flex justify-between items-center">
                        <h3 className="font-medium text-gray-900 dark:text-white">{chat.name}</h3>
                        {chat.unreadCount > 0 && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                            {chat.unreadCount}
                          </span>
                        )}
                      </div>
                      {chat.lastMessage && (
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 truncate">
                          {chat.lastMessage}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Main content */}
              <div className="flex-1">
                {/* Tabs for response filtering */}
                <div className="mb-6 border-b border-gray-200 dark:border-gray-700">
                  <nav className="-mb-px flex space-x-8">
                    {[
                      { id: 'pending', name: 'Pending', count: responses.filter(r => r.status === 'pending').length },
                      { id: 'approved', name: 'Approved', count: responses.filter(r => r.status === 'approved').length },
                      { id: 'denied', name: 'Denied', count: responses.filter(r => r.status === 'denied').length },
                      { id: 'all', name: 'All', count: responses.length }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setSelectedTab(tab.id as 'pending' | 'approved' | 'denied' | 'all')}
                        className={`
                          whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                          ${selectedTab === tab.id
                            ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
                          }
                        `}
                      >
                        {tab.name}
                        <span className="ml-2 py-0.5 px-2 rounded-full text-xs font-normal
                          bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                        >
                          {tab.count}
                        </span>
                      </button>
                    ))}
                  </nav>
                </div>

                {/* Selected chat messages and responses */}
                {selectedChat ? (
                  <div className="space-y-6">
                    {selectedChatMessages.map(message => {
                      // Find any response associated with this message
                      const response = responses.find(r => r.messageId === message.id);
                      
                      return (
                        <div key={message.id} className="space-y-4">
                          {/* User message */}
                          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                            <div className="flex justify-between items-start">
                              <div className="flex items-center">
                                <div className="font-medium text-gray-900 dark:text-white">{message.sender.name}</div>
                                <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                                  {new Date(message.timestamp).toLocaleString()}
                                </span>
                              </div>
                            </div>
                            <div className="mt-2 text-gray-700 dark:text-gray-300">
                              {message.content}
                            </div>
                          </div>
                          
                          {/* Generated response (if exists) */}
                          {response && (
                            <div className={`rounded-lg shadow p-4 ml-8 
                              ${response.status === 'approved' ? 'bg-green-50 dark:bg-green-900' : 
                               response.status === 'denied' ? 'bg-red-50 dark:bg-red-900' : 
                               'bg-yellow-50 dark:bg-yellow-900'}`}>
                              <div className="flex justify-between items-start">
                                <div className="font-medium text-gray-900 dark:text-white">Generated Response</div>
                                <div className="flex items-center">
                                  <span className="text-sm mr-2">
                                    Confidence: {(response.confidence * 100).toFixed(0)}%
                                  </span>
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium
                                    ${response.status === 'approved' ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100' : 
                                     response.status === 'denied' ? 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100' : 
                                     'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-100'}`}>
                                    {response.status.charAt(0).toUpperCase() + response.status.slice(1)}
                                  </span>
                                </div>
                              </div>
                              <div className="mt-2 text-gray-700 dark:text-gray-300">
                                {response.content}
                              </div>
                              
                              {/* Action buttons for pending responses */}
                              {response.status === 'pending' && (
                                <div className="mt-4 flex space-x-2 justify-end">
                                  <button
                                    onClick={() => handleDenyResponse(response.id)}
                                    className="px-3 py-1 bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100 rounded hover:bg-red-200 dark:hover:bg-red-700"
                                  >
                                    Deny
                                  </button>
                                  <button
                                    onClick={() => handleApproveResponse(response.id)}
                                    className="px-3 py-1 bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 rounded hover:bg-green-200 dark:hover:bg-green-700"
                                  >
                                    Approve
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
                    <p className="text-gray-500 dark:text-gray-400">
                      Select a chat to view messages and responses
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
} 