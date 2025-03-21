import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  Divider,
  Button,
  CircularProgress,
  TextField,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SendIcon from '@mui/icons-material/Send';
import CancelIcon from '@mui/icons-material/Cancel';
import RefreshIcon from '@mui/icons-material/Refresh';
import ClearIcon from '@mui/icons-material/Clear';
import PersonIcon from '@mui/icons-material/Person';
import { Response, ResponseStatus } from '../../types';
import { DialogMessage } from '../../types/dialog';

interface ConversationViewProps {
  selectedResponse: Response | null;
  dialogMessages: DialogMessage[];
  loadingMessages: boolean;
  onGenerate: () => void;
  onSend: (response: string) => void;
  onClear: () => void;
  onRetry: () => void;
}

const ConversationView: React.FC<ConversationViewProps> = ({
  selectedResponse,
  dialogMessages,
  loadingMessages,
  onGenerate,
  onSend,
  onClear,
  onRetry,
}) => {
  const [userInput, setUserInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'instant' });
    }
  };

  useEffect(() => {
    if (!loadingMessages && dialogMessages.length > 0) {
      scrollToBottom();
    }
  }, [dialogMessages, loadingMessages]);

  if (!selectedResponse) {
    return (
      <Paper sx={{ 
        height: '100%', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        p: 4
      }}>
        <Typography variant="body1" color="text.secondary">
          Select a dialog to view the conversation
        </Typography>
      </Paper>
    );
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUserInput(e.target.value);
  };

  const handleSend = () => {
    if (userInput.trim() || selectedResponse.suggested_response) {
      onSend(userInput.trim() || selectedResponse.suggested_response);
      setUserInput('');
    }
  };

  const renderResponseBox = () => {
    switch (selectedResponse.status) {
      case ResponseStatus.GENERATING:
        return (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%'
          }}>
            <CircularProgress size={24} />
            <Typography variant="body1" sx={{ ml: 2 }}>
              Generating response...
            </Typography>
            <Button 
              startIcon={<CancelIcon />}
              color="error"
              onClick={onClear}
              sx={{ ml: 2 }}
            >
              Cancel
            </Button>
          </Box>
        );

      case ResponseStatus.FAILED:
        return (
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center',
            height: '100%'
          }}>
            <Typography variant="body1" color="error" sx={{ mb: 2 }}>
              Failed to generate response
            </Typography>
            <Box>
              <Button 
                startIcon={<RefreshIcon />}
                color="primary"
                onClick={onRetry}
                sx={{ mr: 2 }}
              >
                Retry
              </Button>
              <Button 
                startIcon={<ClearIcon />}
                color="error"
                onClick={onClear}
              >
                Clear
              </Button>
            </Box>
          </Box>
        );

      case ResponseStatus.PENDING_APPROVAL:
      default:
        return (
          <>
            <TextField
              multiline
              fullWidth
              rows={4}
              value={userInput || selectedResponse.suggested_response || ''}
              onChange={handleInputChange}
              placeholder="Type your reply or generate an AI response..."
              variant="outlined"
              sx={{ mb: 2 }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
              {!userInput && !selectedResponse.suggested_response && (
                <Button 
                  startIcon={<SmartToyIcon />}
                  color="primary"
                  onClick={onGenerate}
                >
                  Generate AI Response
                </Button>
              )}
              {(userInput || selectedResponse.suggested_response) && (
                <>
                  <Button 
                    startIcon={<ClearIcon />}
                    color="error"
                    onClick={() => {
                      setUserInput('');
                      onClear();
                    }}
                  >
                    Clear
                  </Button>
                  <Button 
                    startIcon={<SendIcon />}
                    color="primary"
                    variant="contained"
                    onClick={handleSend}
                  >
                    Send
                  </Button>
                </>
              )}
            </Box>
          </>
        );
    }
  };

  // Get status chip based on status
  const getStatusChip = (status: string) => {
    switch (status) {
      case ResponseStatus.GENERATING:
        return <Chip label="Generating..." color="warning" size="small" />;
      case ResponseStatus.FAILED:
        return <Chip label="Failed" color="error" size="small" />;
      case ResponseStatus.PENDING_APPROVAL:
      default:
        return <Chip label="Pending Approval" color="info" size="small" />;
    }
  };

  // Render message bubble
  const renderMessageBubble = (message: DialogMessage) => {
    const isSelf = message.sender.is_self;
    
    return (
      <Box
        key={message.id}
        sx={{
          display: 'flex',
          justifyContent: isSelf ? 'flex-end' : 'flex-start',
          mb: 2
        }}
      >
        {!isSelf && (
          <Avatar sx={{ mr: 1, bgcolor: 'secondary.main' }}>
            <PersonIcon />
          </Avatar>
        )}
        <Paper
          elevation={1}
          sx={{
            p: 2,
            maxWidth: '70%',
            bgcolor: isSelf ? 'primary.light' : 'background.default',
            color: isSelf ? 'primary.contrastText' : 'text.primary',
            borderRadius: 2,
            position: 'relative'
          }}
        >
          <Typography variant="body1">{message.text}</Typography>
          <Typography variant="caption" sx={{ display: 'block', mt: 1, color: isSelf ? 'rgba(255,255,255,0.7)' : 'text.secondary' }}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Typography>
        </Paper>
        {isSelf && (
          <Avatar sx={{ ml: 1, bgcolor: 'primary.main' }}>
            <PersonIcon />
          </Avatar>
        )}
      </Box>
    );
  };
  
  return (
    <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Dialog header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Avatar sx={{ mr: 1 }}>{selectedResponse.dialog_name.charAt(0).toUpperCase()}</Avatar>
        <Box>
          <Typography variant="h6">{selectedResponse.dialog_name}</Typography>
          <Typography variant="caption" color="text.secondary">
            Last message: {new Date(selectedResponse.last_message_timestamp).toLocaleString()}
          </Typography>
        </Box>
        <Box sx={{ ml: 'auto' }}>
          {getStatusChip(selectedResponse.status)}
        </Box>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Message history */}
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto',
        mb: 2,
        display: 'flex',
        flexDirection: 'column-reverse',
        minHeight: '200px'
      }}>
        {loadingMessages ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : dialogMessages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', my: 4 }}>
            No message history available
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column-reverse' }}>
            <div ref={messagesEndRef} style={{ height: 1 }} />
            {dialogMessages.map(message => renderMessageBubble(message))}
          </Box>
        )}
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Response box */}
      <Card variant="outlined" sx={{ mb: 2, minHeight: '200px' }}>
        <CardContent>
          {renderResponseBox()}
        </CardContent>
      </Card>
    </Paper>
  );
};

export default ConversationView; 