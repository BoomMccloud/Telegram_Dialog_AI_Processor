import React, { useState } from 'react';
import { MainLayout } from '@components/Layout/MainLayout';
import { MessageThread } from '@components/Messages/MessageThread';
import { MessageContextView } from '@components/Messages/MessageContextView';
import { useDialogs, DialogFilterMode } from '@hooks/useDialogs';
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
  Tabs,
  Tab,
  Paper,
  Breadcrumbs,
  Link,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import ChatIcon from '@mui/icons-material/Chat';
import GroupIcon from '@mui/icons-material/Group';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

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
    setFilterMode
  } = useDialogs();

  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [view, setView] = useState<'dialogs' | 'messages' | 'context'>('dialogs');

  const handleMessageSelect = (messageId: string) => {
    setSelectedMessageId(messageId);
    setView('context');
  };

  const handleRefresh = () => {
    fetchDialogs();
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: DialogFilterMode) => {
    setFilterMode(newValue);
    setSelectedDialogId(null);
    setSelectedMessageId(null);
    setView('dialogs');
  };

  const handleDialogSelect = (dialogId: string) => {
    setSelectedDialogId(dialogId);
    setView('messages');
  };

  const handleBreadcrumbClick = (newView: 'dialogs' | 'messages' | 'context') => {
    if (newView === 'dialogs') {
      setSelectedDialogId(null);
      setSelectedMessageId(null);
    } else if (newView === 'messages') {
      setSelectedMessageId(null);
    }
    setView(newView);
  };

  if (loading) {
    return (
      <MainLayout>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          height: 'calc(100vh - 64px)'
        }}>
          <CircularProgress />
        </Box>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error.message}
        </Alert>
      </MainLayout>
    );
  }

  const getDialogCount = (mode: DialogFilterMode) => {
    switch (mode) {
      case 'all-unread':
        return dialogs.filter(d => d.unread_count > 0).length;
      case 'unread-dms':
        return dialogs.filter(d => d.unread_count > 0 && !d.is_group).length;
      case 'unread-groups':
        return dialogs.filter(d => d.unread_count > 0 && d.is_group).length;
      case 'all':
        return dialogs.length;
      default:
        return 0;
    }
  };

  const renderDialogList = () => (
    <List sx={{ 
      overflowY: 'auto',
      height: '100%',
      '& .MuiListItem-root': {
        px: 1,
      }
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

  return (
    <MainLayout>
      <Box sx={{ p: 2, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
        {/* Top Navigation */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />}>
              <Link
                component="button"
                variant="body1"
                onClick={() => handleBreadcrumbClick('dialogs')}
                color={view === 'dialogs' ? 'text.primary' : 'inherit'}
                underline={view === 'dialogs' ? 'none' : 'hover'}
              >
                Dialogs
              </Link>
              {selectedDialog && (view === 'messages' || view === 'context') && (
                <Link
                  component="button"
                  variant="body1"
                  onClick={() => handleBreadcrumbClick('messages')}
                  color={view === 'messages' ? 'text.primary' : 'inherit'}
                  underline={view === 'messages' ? 'none' : 'hover'}
                >
                  {selectedDialog.title}
                </Link>
              )}
              {view === 'context' && (
                <Typography color="text.primary">
                  Message Context
                </Typography>
              )}
            </Breadcrumbs>
            <Tooltip title="Refresh">
              <IconButton onClick={handleRefresh} disabled={loading} size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
          <Tabs
            value={filterMode}
            onChange={handleTabChange}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab 
              label={`All Unread (${getDialogCount('all-unread')})`} 
              value="all-unread"
            />
            <Tab 
              label={`Unread DMs (${getDialogCount('unread-dms')})`} 
              value="unread-dms"
            />
            <Tab 
              label={`Unread Groups (${getDialogCount('unread-groups')})`} 
              value="unread-groups"
            />
            <Tab 
              label={`All (${getDialogCount('all')})`} 
              value="all"
            />
          </Tabs>
        </Box>

        {/* Main Content */}
        <Paper 
          elevation={2} 
          sx={{ 
            flexGrow: 1,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {view === 'dialogs' && renderDialogList()}
          
          {view === 'messages' && selectedDialogId && (
            <MessageThread
              dialogId={selectedDialogId}
              onMessageSelect={handleMessageSelect}
              onDialogSelect={setSelectedDialogId}
            />
          )}
          
          {view === 'context' && selectedMessageId && selectedDialogId && (
            <MessageContextView
              messageId={selectedMessageId}
              dialogId={selectedDialogId}
            />
          )}

          {/* Empty States */}
          {view === 'messages' && !selectedDialogId && (
            <Box sx={{ 
              p: 3, 
              textAlign: 'center', 
              color: 'text.secondary',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Typography variant="body1">
                Select a dialog to view messages
              </Typography>
            </Box>
          )}
          
          {view === 'context' && !selectedMessageId && (
            <Box sx={{ 
              p: 3, 
              textAlign: 'center', 
              color: 'text.secondary',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Typography variant="body1">
                Select a message to view its context
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>
    </MainLayout>
  );
};

export default TelegramMessagesPage; 