import React from 'react';
import { 
  Alert, 
  CircularProgress, 
  List, 
  ListItem, 
  ListItemButton, 
  ListItemText, 
  Typography,
  IconButton,
  Badge,
  Box,
  Tooltip,
  Paper,
  Button,
  Drawer,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import ChatIcon from '@mui/icons-material/Chat';
import GroupIcon from '@mui/icons-material/Group';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ConversationView from '@components/ConversationView';
import { useDialogs, DialogFilterMode } from '@hooks/useDialogs';

// Constants
const DRAWER_WIDTH = 320;

const TelegramMessagesPage: React.FC = () => {
  const {
    dialogs,
    filteredDialogs,
    loading,
    error,
    selectedDialogId,
    setSelectedDialogId,
    fetchDialogs,
    filterMode,
    setFilterMode,
    initialized,
  } = useDialogs();

  const handleRefresh = () => {
    fetchDialogs();
  };

  const handleTabChange = (newValue: DialogFilterMode) => {
    setFilterMode(newValue);
    setSelectedDialogId(null);
  };

  const handleDialogSelect = (dialogId: string) => {
    setSelectedDialogId(dialogId);
  };

  // Base layout that's consistent across all states
  const renderBaseLayout = (content: React.ReactNode) => (
    <Box sx={{ 
      display: 'flex', 
      height: 'calc(100vh - 64px)',
      overflow: 'hidden'
    }}>
      {/* Left Drawer - Always present */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            position: 'relative',
            height: '100%',
            border: 'none',
          },
        }}
      >
        <Box sx={{ 
          p: 2, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: 1,
          borderColor: 'divider'
        }}>
          <Typography variant="h6">Dialogs</Typography>
          <Tooltip title="Refresh messages">
            <IconButton onClick={handleRefresh} disabled={loading} size="medium">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
        
        {initialized && (
          <Box sx={{ 
            p: 1,
            display: 'flex',
            gap: 1,
            borderBottom: 1,
            borderColor: 'divider'
          }}>
            <Button 
              size="small"
              variant={filterMode === 'all-unread' ? 'contained' : 'text'}
              onClick={() => handleTabChange('all-unread')}
            >
              Unread
            </Button>
            <Button
              size="small"
              variant={filterMode === 'all' ? 'contained' : 'text'}
              onClick={() => handleTabChange('all')}
            >
              All
            </Button>
          </Box>
        )}

        {initialized ? renderDialogList() : (
          <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
            Click the button to load dialogs
          </Box>
        )}
      </Drawer>

      {/* Main Content Area - Always present */}
      <Box sx={{ 
        flexGrow: 1,
        height: '100%',
        overflow: 'hidden',
        bgcolor: 'background.default'
      }}>
        {content}
      </Box>
    </Box>
  );

  if (loading) {
    return renderBaseLayout(
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        height: '100%'
      }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return renderBaseLayout(
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error.message}
        </Alert>
      </Box>
    );
  }

  if (!initialized) {
    return renderBaseLayout(
      <Box sx={{ 
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        p: 3
      }}>
        <Paper 
          elevation={2} 
          sx={{ 
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            maxWidth: 400
          }}
        >
          <Typography variant="h6" color="text.secondary" align="center">
            Ready to fetch your Telegram messages
          </Typography>
          <Typography variant="body1" color="text.secondary" align="center">
            Click the button below to start loading your messages
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={fetchDialogs}
            startIcon={<PlayArrowIcon />}
            disabled={loading}
          >
            Start Loading Messages
          </Button>
        </Paper>
      </Box>
    );
  }

  const renderDialogList = () => (
    <List sx={{ 
      width: '100%',
      bgcolor: 'background.paper',
      height: '100%',
      overflow: 'auto',
    }}>
      {filteredDialogs.length === 0 ? (
        <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
          No messages in this category
        </Box>
      ) : (
        filteredDialogs.map((dialog) => (
          <ListItem key={dialog.id} disablePadding>
            <ListItemButton
              selected={selectedDialogId === dialog.id.toString()}
              onClick={() => handleDialogSelect(dialog.id.toString())}
              sx={{
                borderRadius: 1,
                mx: 1,
                '&.Mui-selected': {
                  backgroundColor: 'action.selected',
                }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                {dialog.is_group ? 
                  <GroupIcon sx={{ mr: 1, color: 'text.secondary' }} /> : 
                  <ChatIcon sx={{ mr: 1, color: 'text.secondary' }} />
                }
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <Typography variant="body1" noWrap sx={{ flex: 1 }}>
                        {dialog.title}
                      </Typography>
                      {dialog.unread_count > 0 && (
                        <Badge
                          badgeContent={dialog.unread_count}
                          color="primary"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  }
                />
              </Box>
            </ListItemButton>
          </ListItem>
        ))
      )}
    </List>
  );

  const selectedDialog = dialogs.find(d => d.id.toString() === selectedDialogId);

  return renderBaseLayout(
    <ConversationView
      selectedResponse={selectedDialog ? {
        id: selectedDialog.id.toString(),
        dialog_id: selectedDialog.id.toString(),
        dialog_name: selectedDialog.title,
        suggested_response: "Loading...", // This will be replaced with actual response
        edited_response: "",
        status: "PENDING_APPROVAL",
        processed_at: new Date().toISOString(),
        last_message_timestamp: new Date().toISOString(),
        last_message_id: "0",
        model_name: "gpt-4",
      } : null}
      dialogMessages={[]} // This will be populated with actual messages
      loadingMessages={false}
      onReject={() => {}}
      onEdit={() => {}}
      onApprove={() => {}}
      onSend={() => {}}
    />
  );
};

export default TelegramMessagesPage; 