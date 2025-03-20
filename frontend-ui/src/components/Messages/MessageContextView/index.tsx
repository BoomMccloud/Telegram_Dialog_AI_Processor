import React from 'react';

interface MessageContextViewProps {
  messageId: string;
  dialogId: string;
}

export const MessageContextView: React.FC<MessageContextViewProps> = ({
  messageId,
  dialogId
}) => {
  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {/* Message context will be displayed here */}
          <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Dialog ID: {dialogId}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Message ID: {messageId}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageContextView; 