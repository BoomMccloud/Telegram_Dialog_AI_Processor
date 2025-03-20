import React from 'react';

interface MessageThreadProps {
  dialogId: string;
  onMessageSelect: (messageId: string) => void;
  onDialogSelect: (dialogId: string) => void;
}

export const MessageThread: React.FC<MessageThreadProps> = ({
  dialogId,
  onMessageSelect,
  onDialogSelect
}) => {
  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="flex-1 overflow-y-auto p-4">
        {/* Message list will be implemented here */}
        <div className="space-y-4">
          {/* Placeholder for message items */}
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
            Message thread content will be displayed here
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageThread; 