import { useState, useCallback } from 'react';
import { api } from '../services/api';

interface UseDialogUUIDResult {
  uuid: string | null;
  loading: boolean;
  error: Error | null;
  getUUID: () => Promise<string | null>;
}

/**
 * Hook to convert a Telegram dialog ID to internal UUID
 * @param telegramId The Telegram dialog ID to convert
 * @returns Object containing the UUID, loading state, error state, and refresh function
 */
export const useDialogUUID = (telegramId: string | null): UseDialogUUIDResult => {
  const [uuid, setUUID] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const getUUID = useCallback(async () => {
    if (!telegramId) {
      setUUID(null);
      return null;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.dialogs.getByTelegramId(telegramId);
      const uuid = response.selection_id;
      setUUID(uuid);
      return uuid;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to get dialog UUID');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [telegramId]);

  return { uuid, loading, error, getUUID };
}; 