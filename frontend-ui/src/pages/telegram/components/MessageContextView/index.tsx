import React, { useEffect } from 'react';
import { MessageContext } from '../../types';
import { useMessageContext } from '../../hooks/useMessageContext';

interface MessageContextViewProps {
  dialogId: string;
  messageId: string;
  onContextLoad: (context: MessageContext) => void;
  className?: string;
}

export const MessageContextView: React.FC<MessageContextViewProps> = ({
  dialogId,
  messageId,
  onContextLoad,
  className = ''
}) => {
  const {
    context,
    loadMore,
    hasMore,
    isLoading
  } = useMessageContext(dialogId, messageId);

  // Notify parent when context changes
  useEffect(() => {
    onContextLoad(context);
  }, [context, onContextLoad]);

  return (
    <div className={`message-context-view ${className}`}>
      <div className="context-messages">
        {context.messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.isCurrentUser ? 'sent' : 'received'}`}
          >
            <div className="message-sender">{message.sender.name}</div>
            <div className="message-content">{message.content}</div>
            <div className="message-time">{message.timestamp}</div>
          </div>
        ))}
      </div>
      
      {hasMore && (
        <div className="context-actions">
          <button
            onClick={loadMore}
            disabled={isLoading}
            className="load-more-btn"
          >
            {isLoading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
};

export default MessageContextView; 