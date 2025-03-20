import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
  Tabs,
  Tab,
  Badge,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import LoginIcon from '@mui/icons-material/Login';
import LogoutIcon from '@mui/icons-material/Logout';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import { Response, ResponseStatus, BaseDialog } from '../../types';
import { checkAuthentication } from '../../services/auth';
import { api } from '../../services/api';
import PhoneAuth from '../../components/Auth/PhoneAuth';
import ProcessingDialog from '../../components/ProcessingDialog';
import TabPanel from '../../components/TabPanel';
import DialogList from '../../components/DialogList';
import ConversationView from '../../components/ConversationView';
import { useResponses } from '../../hooks/useResponses';
import { useDialogs } from '../../hooks/useDialogs';

// Remove local component declarations
const Messages = () => {
  // Tab state
  const [tabValue, setTabValue] = useState(0);
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Edit dialog state
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [editedText, setEditedText] = useState('');
  
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [phoneDialogOpen, setPhoneDialogOpen] = useState(false);

  // Use our custom hooks
  const {
    pendingResponses,
    historyResponses,
    totalPending,
    totalHistory,
    selectedResponse,
    loading: responsesLoading,
    error: responsesError,
    fetchPendingResponses,
    fetchHistoryResponses,
    approveResponse,
    rejectResponse,
    updateResponse,
    sendResponse,
    setSelectedResponse,
    setPendingResponses,
    setHistoryResponses,
    setTotalPending,
    setTotalHistory
  } = useResponses();

  const {
    dialogs,
    selectedDialog,
    dialogMessages,
    loading: dialogsLoading,
    loadingMessages,
    error: dialogsError,
    fetchDialogs,
    fetchDialogMessages,
    setSelectedDialog,
    isProcessing,
    processingProgress,
    startProcessing,
    cancelProcessing
  } = useDialogs();

  // Handle tab change
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Reset search and selection when switching tabs
    setSearchQuery('');
    setSelectedResponse(null);
  };

  // Effects for initialization and tab changes
  useEffect(() => {
    if (tabValue === 0) {
      fetchPendingResponses();
    } else {
      fetchHistoryResponses(statusFilter !== 'all' ? statusFilter : undefined);
    }
  }, [tabValue, statusFilter]);

  // Check authentication on component mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const isAuth = await checkAuthentication();
        setIsAuthenticated(isAuth);
        
        // If authenticated, fetch data based on current tab
        if (isAuth) {
          if (tabValue === 0) {
            fetchDialogs();
            fetchPendingResponses();
          } else {
            fetchHistoryResponses();
          }
        }
      } catch (error) {
        console.error('Error checking authentication status:', error);
      }
    };
    
    checkAuthStatus();
  }, []);

  // Open edit dialog
  const handleOpenEditDialog = () => {
    if (!selectedResponse) return;
    setEditedText(selectedResponse.edited_response || selectedResponse.suggested_response);
    setOpenEditDialog(true);
  };

  // Close edit dialog
  const handleCloseEditDialog = () => {
    setOpenEditDialog(false);
    setEditedText('');
  };

  // Save edited response
  const handleSaveEdit = async () => {
    if (!selectedResponse) return;
    const success = await updateResponse(selectedResponse.id, editedText);
    if (success) {
      handleCloseEditDialog();
    }
  };

  // Select response handler
  const handleSelectResponse = (response: Response) => {
    setSelectedResponse(response);
    fetchDialogMessages(response.dialog_id);
  };

  // Select dialog handler
  const handleDialogSelect = async (dialog: BaseDialog) => {
    setSelectedDialog(dialog);
    try {
      // First, get the dialog details including the UUID
      const dialogDetails = await api.dialogs.getByTelegramId(dialog.id.toString());
      const dialogUUID = dialogDetails.selection_id; // This is the UUID we need
      
      // Fetch responses for the selected dialog
      const pendingResp = await api.responses.getPending(0, 100);
      const historyResp = await api.responses.getHistory(0, 100);
      
      // Filter responses using the dialog UUID
      const filteredPending = pendingResp.responses.filter(r => r.dialog_id === dialogUUID);
      const filteredHistory = historyResp.responses.filter(r => r.dialog_id === dialogUUID);
      
      // Update state
      setPendingResponses(filteredPending);
      setHistoryResponses(filteredHistory);
      setTotalPending(filteredPending.length);
      setTotalHistory(filteredHistory.length);

      // If we have a pending response, select it automatically
      if (filteredPending.length > 0) {
        handleSelectResponse(filteredPending[0]);
      } else if (filteredHistory.length > 0) {
        // If no pending responses, select the most recent history response
        handleSelectResponse(filteredHistory[0]);
      }
    } catch (err) {
      console.error('Error processing dialog:', err);
    }
  };

  // Handle phone authentication success
  const handlePhoneAuthSuccess = () => {
    setIsAuthenticated(true);
    setPhoneDialogOpen(false);
    if (tabValue === 0) {
      fetchDialogs();
      fetchPendingResponses();
    } else {
      fetchHistoryResponses();
    }
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      await api.auth.logout();
      setIsAuthenticated(false);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    } catch (error) {
      console.error('Failed to logout:', error);
    }
  };

  // Handle delete messages
  const handleDeleteMessages = () => {
    console.log('Delete messages functionality to be implemented');
  };

  // Get error message to display
  const getErrorMessage = () => {
    return responsesError || dialogsError || authError;
  };

  // Handle refresh button click
  const handleRefresh = () => {
    startProcessing();
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Message Responses
      </Typography>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mb: 2 }}>
        {isAuthenticated ? (
          <>
            <Button
              variant="contained"
              color="error"
              onClick={handleDeleteMessages}
              startIcon={<DeleteIcon />}
            >
              Delete Messages
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleRefresh}
              disabled={isProcessing}
              startIcon={<RefreshIcon />}
            >
              Refresh Messages
            </Button>
            <Button
              variant="outlined"
              color="error"
              startIcon={<LogoutIcon />}
              onClick={handleLogout}
              disabled={isProcessing}
            >
              Logout
            </Button>
          </>
        ) : (
          <Button
            variant="contained"
            color="primary"
            startIcon={<LoginIcon />}
            onClick={() => setPhoneDialogOpen(true)}
            disabled={isProcessing}
          >
            Login
          </Button>
        )}
      </Box>
      
      {getErrorMessage() && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          onClose={() => setAuthError(null)} // Only clear auth errors here
        >
          {getErrorMessage()}
        </Alert>
      )}
      
      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange}
          aria-label="message tabs"
        >
          <Tab 
            label={
              <Badge badgeContent={totalPending} color="error" max={99}>
                Pending Approval
              </Badge>
            } 
            id="messages-tab-0"
            aria-controls="messages-tabpanel-0"
          />
          <Tab 
            label={
              <Badge badgeContent={totalHistory} color="primary" max={99}>
                History
              </Badge>
            } 
            id="messages-tab-1"
            aria-controls="messages-tabpanel-1"
          />
        </Tabs>
      </Box>
      
      {/* Main content */}
      <Box sx={{ display: 'flex', mt: 2 }}>
        {/* Left panel - Dialog/Response list */}
        <Box sx={{ width: 320, mr: 2 }}>
          <Box sx={{ mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              placeholder={tabValue === 0 ? "Search dialogs..." : "Search responses..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
              }}
            />
          </Box>
          
          <TabPanel value={tabValue} index={0}>
            {tabValue === 0 && (
              <>
                <DialogList
                  loading={dialogsLoading}
                  items={dialogs}
                  selectedItemId={selectedDialog?.id || null}
                  searchQuery={searchQuery}
                  isPending={true}
                  onSelectItem={(item) => handleDialogSelect(item as BaseDialog)}
                />
                {pendingResponses.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Pending Responses: {pendingResponses.length}
                    </Typography>
                  </Box>
                )}
              </>
            )}
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            <Box sx={{ mb: 2 }}>
              <FormControl size="small" fullWidth>
                <InputLabel id="status-filter-label">Status</InputLabel>
                <Select
                  labelId="status-filter-label"
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value={ResponseStatus.APPROVED}>Approved</MenuItem>
                  <MenuItem value={ResponseStatus.REJECTED}>Rejected</MenuItem>
                  <MenuItem value={ResponseStatus.SENT}>Sent</MenuItem>
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
                onSelectItem={(item) => handleSelectResponse(item as Response)}
              />
            )}
          </TabPanel>
        </Box>
        
        {/* Right panel - Conversation view */}
        <Box sx={{ flexGrow: 1 }}>
          <ConversationView
            selectedResponse={selectedResponse}
            dialogMessages={dialogMessages}
            loadingMessages={loadingMessages}
            onReject={() => rejectResponse(selectedResponse?.id || '')}
            onEdit={handleOpenEditDialog}
            onApprove={() => approveResponse(selectedResponse?.id || '')}
            onSend={() => sendResponse(selectedResponse?.id || '')}
          />
        </Box>
      </Box>
      
      {/* Edit Dialog */}
      <Dialog open={openEditDialog} onClose={handleCloseEditDialog} maxWidth="md" fullWidth>
        <DialogTitle>Edit Response</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Edit the suggested response below:
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            label="Response"
            fullWidth
            multiline
            rows={6}
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            variant="outlined"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleSaveEdit} color="primary" variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Phone Authentication Dialog */}
      <Dialog 
        open={phoneDialogOpen} 
        onClose={() => setPhoneDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Authenticate with Telegram</DialogTitle>
        <DialogContent>
          <Box sx={{ p: 2 }}>
            <PhoneAuth 
              onSuccess={handlePhoneAuthSuccess}
              onCancel={() => setPhoneDialogOpen(false)}
            />
          </Box>
        </DialogContent>
      </Dialog>
      
      {/* Processing Dialog */}
      <ProcessingDialog 
        open={isProcessing} 
        progress={processingProgress} 
        onCancel={cancelProcessing}
      />
    </Box>
  );
};

export default Messages; 