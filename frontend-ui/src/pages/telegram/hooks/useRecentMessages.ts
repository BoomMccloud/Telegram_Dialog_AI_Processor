import { useState, useEffect } from 'react';
import { HistoricalMessage } from '../types';
import { api } from '../../../services/api';

interface UseRecentMessagesResult {
  messages: HistoricalMessage[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

interface TelegramMessage {
  message_id: number;
  text: string;
  sender: {
    id: number;
    name: string;
  };
  date: string;
  is_outgoing: boolean;
  is_unread: boolean;
  dialog_id: number;
  dialog_name: string | null;
}

const transformMessage = (message: TelegramMessage): HistoricalMessage => ({
  id: message.message_id.toString(),
  content: message.text || '',
  sender: {
    id: message.sender.id.toString(),
    name: message.sender.name || 'Unknown',
  },
  timestamp: message.date,
  isCurrentUser: message.is_outgoing,
});

const sortMessagesByDate = (messages: HistoricalMessage[]): HistoricalMessage[] => {
  return [...messages].sort((a, b) => {
    const dateA = new Date(a.timestamp);
    const dateB = new Date(b.timestamp);
    return dateB.getTime() - dateA.getTime(); // Descending order (newest first)
  });
};

export const useRecentMessages = (dialogId: string | null): UseRecentMessagesResult => {
  const [messages, setMessages] = useState<HistoricalMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchMessages = async () => {
    if (!dialogId) {
      setMessages([]);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      const response = await api.messages.getByDialogId(dialogId, { limit: 100 });
      
      // The API returns an array of messages directly
      if (Array.isArray(response)) {
        const transformedMessages = response.map(transformMessage);
        setMessages(sortMessagesByDate(transformedMessages));
      } else {
        console.error('Unexpected response format:', response);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load messages'));
      setMessages([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [dialogId]);

  return {
    messages,
    isLoading,
    error,
    refetch: fetchMessages
  };
}; 