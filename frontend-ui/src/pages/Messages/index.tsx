import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Box,
  Tabs,
  Tab,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from '@mui/material';
import { useResponses } from '../../hooks/useResponses';
import { Response, ResponseStatus, BaseDialog } from '../../types';
import DialogList from '../../components/DialogList';
import ConversationView from '../../components/ConversationView';
import TabPanel from '../../components/TabPanel';
import { checkAuthentication } from '../../services/auth';
import { api } from '../../services/api';

// Temporary mock for useDialogMessages hook
interface DialogMessage {
  id: string;
  text: string;
  timestamp: string;
  sender: {
    id: string;
    name: string;
    is_self: boolean;
  };
  dialog_id: string;
  is_unread: boolean;
  has_mention: boolean;
}

const useDialogMessages = () => ({
  dialogMessages: [] as DialogMessage[],
  loading: false,
  fetchDialogMessages: async () => {},
});

const Messages = () => {
  const [tabValue, setTabValue] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const {
    pendingResponses,
    historyResponses,
    selectedResponse,
    loading: responsesLoading,
    fetchPendingResponses,
    fetchHistoryResponses,
    sendResponse,
    setSelectedResponse,
  } = useResponses();

  const {
    dialogMessages,
    loading: loadingMessages,
    fetchDialogMessages,
  } = useDialogMessages();

  // Check authentication on component mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const isAuth = await checkAuthentication();
        setIsAuthenticated(isAuth);
        
        if (isAuth) {
          fetchPendingResponses();
        }
      } catch (error) {
        console.error('Error checking authentication status:', error);
      }
    };
    
    checkAuthStatus();
  }, [fetchPendingResponses]);

  // Handle tab change
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (newValue === 0) {
      fetchPendingResponses();
    } else {
      fetchHistoryResponses(statusFilter !== 'all' ? statusFilter : undefined);
    }
  };

  // Handle search
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  // Handle status filter change
  const handleStatusFilterChange = (event: SelectChangeEvent<string>) => {
    setStatusFilter(event.target.value);
    if (tabValue === 1) {
      fetchHistoryResponses(event.target.value !== 'all' ? event.target.value : undefined);
    }
  };

  // Select response handler
  const handleSelectResponse = (item: Response | BaseDialog) => {
    if ('dialog_id' in item) {
      setSelectedResponse(item as Response);
      fetchDialogMessages();
    }
  };

  // Handle generate response
  const handleGenerateResponse = async () => {
    if (!selectedResponse) return;
    try {
      await api.responses.generate.private(selectedResponse.dialog_id);
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.GENERATING
      });
    } catch (error) {
      console.error('Error generating response:', error);
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.FAILED
      });
    }
  };

  // Handle send response
  const handleSendResponse = async () => {
    if (!selectedResponse) return;
    try {
      await sendResponse(selectedResponse.id);
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.PENDING_APPROVAL,
        suggested_response: ''
      });
    } catch (error) {
      console.error('Error sending response:', error);
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.FAILED
      });
    }
  };

  // Handle clear response
  const handleClearResponse = () => {
    if (!selectedResponse) return;
    setSelectedResponse({
      ...selectedResponse,
      status: ResponseStatus.PENDING_APPROVAL,
      suggested_response: ''
    });
  };

  // Handle retry generation
  const handleRetryGeneration = () => {
    handleGenerateResponse();
  };

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default' }}>
      {/* Left panel - Dialog/Response list */}
      <Box sx={{ width: 360, borderRight: 1, borderColor: 'divider' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Unread" />
            <Tab label="History" />
          </Tabs>
        </Box>
        
        <Box sx={{ p: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Search..."
            value={searchQuery}
            onChange={handleSearchChange}
            sx={{ mb: 2 }}
          />
          
          <TabPanel value={tabValue} index={0}>
            <DialogList
              loading={responsesLoading}
              items={pendingResponses}
              selectedItemId={selectedResponse?.id || null}
              searchQuery={searchQuery}
              isPending={true}
              onSelectItem={handleSelectResponse}
            />
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            <Box sx={{ mb: 2 }}>
              <FormControl size="small" fullWidth>
                <InputLabel id="status-filter-label">Status</InputLabel>
                <Select
                  labelId="status-filter-label"
                  value={statusFilter}
                  label="Status"
                  onChange={handleStatusFilterChange}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value={ResponseStatus.PENDING_APPROVAL}>Ready</MenuItem>
                  <MenuItem value={ResponseStatus.FAILED}>Failed</MenuItem>
                </Select>
              </FormControl>
            </Box>
            {tabValue === 1 && (
              <DialogList
                loading={responsesLoading}
                items={historyResponses}
                selectedItemId={selectedResponse?.id || null}
                searchQuery={searchQuery}
                isPending={false}
                onSelectItem={handleSelectResponse}
              />
            )}
          </TabPanel>
        </Box>
      </Box>
      
      {/* Right panel - Conversation view */}
      <Box sx={{ flexGrow: 1 }}>
        <ConversationView
          selectedResponse={selectedResponse}
          dialogMessages={dialogMessages}
          loadingMessages={loadingMessages}
          onGenerate={handleGenerateResponse}
          onSend={handleSendResponse}
          onClear={handleClearResponse}
          onRetry={handleRetryGeneration}
        />
      </Box>
    </Box>
  );
};

export default Messages; 