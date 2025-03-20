export interface HistoricalMessage {
  id: string;
  content: string;
  sender: {
    id: string;
    name: string;
  };
  timestamp: string;
  isCurrentUser: boolean;
}

export interface MessageContext {
  messages: HistoricalMessage[];
  hasMore: boolean;
  isLoading: boolean;
}

export interface MessageContextResponse {
  messages: HistoricalMessage[];
  hasMore: boolean;
} 