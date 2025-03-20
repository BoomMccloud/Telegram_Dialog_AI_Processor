import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
  Avatar,
  Chip,
  Card,
  CardContent,
  CardActions,
  Button,
  CircularProgress,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { Response, ResponseStatus } from '../../types';
import { DialogMessage } from '../../types/dialog';

interface ConversationViewProps {
  selectedResponse: Response | null;
  dialogMessages: DialogMessage[];
  loadingMessages: boolean;
  onReject: () => void;
  onEdit: () => void;
  onApprove: () => void;
  onSend: () => void;
}

const ConversationView: React.FC<ConversationViewProps> = ({
  selectedResponse,
  dialogMessages,
  loadingMessages,
  onReject,
  onEdit,
  onApprove,
  onSend,
}) => {
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

  // Get status chip based on status
  const getStatusChip = (status: string) => {
    switch (status) {
      case ResponseStatus.PENDING_APPROVAL:
        return <Chip label="Pending" color="warning" size="small" />;
      case ResponseStatus.APPROVED:
        return <Chip label="Approved" color="info" size="small" />;
      case ResponseStatus.REJECTED:
        return <Chip label="Rejected" color="error" size="small" />;
      case ResponseStatus.SENT:
        return <Chip label="Sent" color="success" size="small" />;
      case ResponseStatus.FAILED:
        return <Chip label="Failed" color="error" size="small" />;
      default:
        return <Chip label={status} size="small" />;
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
        flexDirection: 'column',
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
          <>
            {dialogMessages.map(message => renderMessageBubble(message))}
          </>
        )}
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* AI suggested response */}
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Avatar sx={{ bgcolor: 'info.main', mr: 1 }}>
              <SmartToyIcon />
            </Avatar>
            <Typography variant="subtitle1">AI Suggested Response</Typography>
          </Box>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
            {selectedResponse.edited_response || selectedResponse.suggested_response}
          </Typography>
        </CardContent>
        <CardActions sx={{ justifyContent: 'flex-end' }}>
          {selectedResponse.status === ResponseStatus.PENDING_APPROVAL && (
            <>
              <Button 
                startIcon={<CancelIcon />} 
                color="error" 
                onClick={onReject}
              >
                Reject
              </Button>
              <Button 
                startIcon={<EditIcon />} 
                color="primary" 
                onClick={onEdit}
              >
                Edit
              </Button>
              <Button 
                startIcon={<CheckCircleIcon />} 
                color="success" 
                variant="contained"
                onClick={onApprove}
              >
                Approve
              </Button>
            </>
          )}
          {selectedResponse.status === ResponseStatus.APPROVED && (
            <>
              <Button 
                startIcon={<EditIcon />} 
                color="primary" 
                onClick={onEdit}
              >
                Edit
              </Button>
              <Button 
                startIcon={<SendIcon />} 
                color="primary" 
                variant="contained"
                onClick={onSend}
              >
                Send
              </Button>
            </>
          )}
          {(selectedResponse.status === ResponseStatus.REJECTED || 
            selectedResponse.status === ResponseStatus.SENT || 
            selectedResponse.status === ResponseStatus.FAILED) && (
            <Button 
              startIcon={<EditIcon />} 
              color="primary" 
              onClick={onEdit}
            >
              View Details
            </Button>
          )}
        </CardActions>
      </Card>
    </Paper>
  );
};

export default ConversationView; 