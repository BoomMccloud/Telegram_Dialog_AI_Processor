import { useState } from 'react';
import { api } from '../services/api';
import { DialogMessage } from '../types/dialog';

interface UseDialogMessagesResult {
  dialogMessages: DialogMessage[];
  loading: boolean;
  error: string | null;
  fetchDialogMessages: (dialogId: string) => Promise<void>;
}

export const useDialogMessages = (): UseDialogMessagesResult => {
  const [dialogMessages, setDialogMessages] = useState<DialogMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDialogMessages = async (dialogId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.messages.getByDialogId(dialogId);
      // Sort messages by timestamp in descending order (newest first)
      const sortedMessages = response.messages
        .map(msg => ({
          id: msg.id,
          text: msg.text,
          timestamp: msg.timestamp,
          sender: msg.sender,
          dialog_id: dialogId,
          is_unread: false,
          has_mention: false
        }))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      
      setDialogMessages(sortedMessages);
    } catch (err) {
      console.error('Error fetching dialog messages:', err);
      setError('Failed to load messages. Please try again.');
      setDialogMessages([]);
    } finally {
      setLoading(false);
    }
  };

  return {
    dialogMessages,
    loading,
    error,
    fetchDialogMessages,
  };
}; 