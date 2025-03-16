import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemButton,
  Avatar,
  Chip,
  TextField,
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
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Badge,
  Card,
  CardContent,
  CardActions,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import HistoryIcon from '@mui/icons-material/History';
import PendingIcon from '@mui/icons-material/Pending';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AuthRequiredDialog from '../../components/Auth/AuthRequiredDialog';
import { api } from '../../services/api';
import { Response, ResponseStatus } from '../../types';

// Tab interface
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

// Tab Panel component
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`messages-tabpanel-${index}`}
      aria-labelledby={`messages-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

// Mock interface for dialog messages - replace with actual API types
interface DialogMessage {
  id: string;
  text: string;
  sender: {
    id: string;
    name: string;
    is_self: boolean;
  };
  timestamp: string;
}

const Messages = () => {
  // Tab state
  const [tabValue, setTabValue] = useState(0);
  
  // State for responses
  const [pendingResponses, setPendingResponses] = useState<Response[]>([]);
  const [historyResponses, setHistoryResponses] = useState<Response[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalPendingResponses, setTotalPendingResponses] = useState(0);
  const [totalHistoryResponses, setTotalHistoryResponses] = useState(0);
  
  // Selected response and dialog
  const [selectedResponse, setSelectedResponse] = useState<Response | null>(null);
  const [dialogMessages, setDialogMessages] = useState<DialogMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  
  // Edit state
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [editedText, setEditedText] = useState('');
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Auth required dialog
  const [showAuthDialog, setShowAuthDialog] = useState(false);

  // Handle tab change
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Reset search and selection when switching tabs
    setSearchQuery('');
    setSelectedResponse(null);
  };

  // Fetch responses on component mount and when filters change
  useEffect(() => {
    if (tabValue === 0) {
      fetchPendingResponses();
    } else {
      fetchHistoryResponses();
    }
  }, [tabValue]);

  // Function to fetch pending responses from API
  const fetchPendingResponses = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getPending(0, 100); // Get more responses for the list
      setPendingResponses(response.responses);
      setTotalPendingResponses(response.total);
    } catch (err: unknown) {
      console.error('Error fetching pending responses:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setShowAuthDialog(true);
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setShowAuthDialog(true);
      } else {
        setError('Failed to load pending responses. Please try again later.');
      }
      
      setPendingResponses([]);
      setTotalPendingResponses(0);
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch history responses from API
  const fetchHistoryResponses = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getHistory(
        0, 
        100, // Get more responses for the list
        statusFilter !== 'all' ? statusFilter : undefined
      );
      
      setHistoryResponses(response.responses);
      setTotalHistoryResponses(response.total);
    } catch (err: unknown) {
      console.error('Error fetching history responses:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setShowAuthDialog(true);
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setShowAuthDialog(true);
      } else {
        setError('Failed to load response history. Please try again later.');
      }
      
      setHistoryResponses([]);
      setTotalHistoryResponses(0);
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch dialog messages
  const fetchDialogMessages = async (dialogId: string) => {
    setLoadingMessages(true);
    
    try {
      // This is a placeholder - you'll need to implement the actual API endpoint
      // const response = await api.messages.getByDialogId(dialogId);
      // setDialogMessages(response.messages);
      
      // Mock data for now - using dialogId in a real implementation
      console.log(`Fetching messages for dialog: ${dialogId}`);
      
      // ... existing code ...

    } catch (err) {
      console.error('Error fetching dialog messages:', err);
      setError('Failed to load dialog messages. Please try again later.');
      setDialogMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  // Refresh current view
  const refreshCurrentView = () => {
    if (tabValue === 0) {
      fetchPendingResponses();
    } else {
      fetchHistoryResponses();
    }
    setSelectedResponse(null);
  };

  // Handle response selection
  const handleSelectResponse = (response: Response) => {
    setSelectedResponse(response);
    fetchDialogMessages(response.dialog_id);
  };

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
    
    try {
      await api.responses.update(selectedResponse.id, { edited_response: editedText });
      
      // Update the selected response with the edited text
      setSelectedResponse({
        ...selectedResponse,
        edited_response: editedText
      });
      
      // Refresh the list to reflect changes
      refreshCurrentView();
      handleCloseEditDialog();
    } catch (err) {
      console.error('Error updating response:', err);
      setError('Failed to update response. Please try again.');
    }
  };

  // Approve response
  const handleApprove = async () => {
    if (!selectedResponse) return;
    
    try {
      await api.responses.approve(selectedResponse.id);
      
      // Update the selected response status
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.APPROVED
      });
      
      // Refresh the list to reflect changes
      refreshCurrentView();
    } catch (err) {
      console.error('Error approving response:', err);
      setError('Failed to approve response. Please try again.');
    }
  };

  // Reject response
  const handleReject = async () => {
    if (!selectedResponse) return;
    
    try {
      await api.responses.reject(selectedResponse.id);
      
      // Update the selected response status
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.REJECTED
      });
      
      // Refresh the list to reflect changes
      refreshCurrentView();
    } catch (err) {
      console.error('Error rejecting response:', err);
      setError('Failed to reject response. Please try again.');
    }
  };

  // Send response
  const handleSend = async () => {
    if (!selectedResponse) return;
    
    try {
      await api.responses.send(selectedResponse.id);
      
      // Update the selected response status
      setSelectedResponse({
        ...selectedResponse,
        status: ResponseStatus.SENT
      });
      
      // Refresh the list to reflect changes
      refreshCurrentView();
    } catch (err) {
      console.error('Error sending response:', err);
      setError('Failed to send response. Please try again.');
    }
  };

  // Filter responses by search query
  const filteredPendingResponses = pendingResponses.filter(response => 
    response.dialog_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    response.suggested_response.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (response.edited_response && response.edited_response.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const filteredHistoryResponses = historyResponses.filter(response => 
    response.dialog_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    response.suggested_response.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (response.edited_response && response.edited_response.toLowerCase().includes(searchQuery.toLowerCase()))
  );

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

  // Render dialog list
  const renderDialogList = (responses: Response[], isPending: boolean) => (
    <List sx={{ width: '100%', bgcolor: 'background.paper', overflow: 'auto', height: 'calc(100vh - 220px)' }}>
      {responses.length === 0 ? (
        <ListItem>
          <ListItemText 
            primary={loading ? "Loading..." : isPending ? "No pending responses" : "No response history"} 
            secondary={loading ? "Please wait..." : isPending ? "All caught up!" : "Try changing filters"} 
          />
        </ListItem>
      ) : (
        responses.map((response) => (
          <ListItemButton
            key={response.id}
            selected={selectedResponse?.id === response.id}
            onClick={() => handleSelectResponse(response)}
            sx={{
              borderLeft: selectedResponse?.id === response.id ? 4 : 0,
              borderColor: 'primary.main',
              '&:hover': { bgcolor: 'action.hover' }
            }}
          >
            <ListItemAvatar>
              <Badge 
                overlap="circular"
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                badgeContent={
                  isPending ? 
                    <PendingIcon color="warning" fontSize="small" /> : 
                    response.status === ResponseStatus.APPROVED ? 
                      <CheckCircleIcon color="info" fontSize="small" /> :
                      response.status === ResponseStatus.SENT ?
                        <SendIcon color="success" fontSize="small" /> :
                        <CancelIcon color="error" fontSize="small" />
                }
              >
                <Avatar>{response.dialog_name.charAt(0).toUpperCase()}</Avatar>
              </Badge>
            </ListItemAvatar>
            <ListItemText 
              primary={response.dialog_name} 
              secondary={
                <Typography
                  sx={{ display: 'inline', color: 'text.secondary' }}
                  component="span"
                  variant="body2"
                  noWrap
                >
                  {new Date(response.processed_at).toLocaleString()} 
                  {!isPending && ` · ${response.status}`}
                </Typography>
              }
            />
          </ListItemButton>
        ))
      )}
    </List>
  );

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

  // Render conversation view
  const renderConversationView = () => {
    if (!selectedResponse) {
      return (
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: 'calc(100vh - 180px)',
          bgcolor: 'background.default',
          borderRadius: 1
        }}>
          <Typography variant="h6" color="text.secondary">
            Select a response to view the conversation
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            The conversation history will appear here
          </Typography>
        </Box>
      );
    }

    return (
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: 'calc(100vh - 180px)',
        bgcolor: 'background.default',
        borderRadius: 1,
        p: 2
      }}>
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
          flexDirection: 'column'
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
                  onClick={handleReject}
                >
                  Reject
                </Button>
                <Button 
                  startIcon={<EditIcon />} 
                  color="primary" 
                  onClick={handleOpenEditDialog}
                >
                  Edit
                </Button>
                <Button 
                  startIcon={<CheckCircleIcon />} 
                  color="success" 
                  variant="contained"
                  onClick={handleApprove}
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
                  onClick={handleOpenEditDialog}
                >
                  Edit
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
            {(selectedResponse.status === ResponseStatus.REJECTED || 
              selectedResponse.status === ResponseStatus.SENT || 
              selectedResponse.status === ResponseStatus.FAILED) && (
              <Button 
                startIcon={<EditIcon />} 
                color="primary" 
                onClick={handleOpenEditDialog}
              >
                View Details
              </Button>
            )}
          </CardActions>
        </Card>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Message Responses
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={tabValue} 
          onChange={handleTabChange} 
          aria-label="message response tabs"
        >
          <Tab 
            icon={<PendingIcon />} 
            iconPosition="start" 
            label={`Pending Responses (${totalPendingResponses})`}
            id="messages-tab-0" 
            aria-controls="messages-tabpanel-0" 
          />
          <Tab 
            icon={<HistoryIcon />} 
            iconPosition="start" 
            label={`Response History (${totalHistoryResponses})`}
            id="messages-tab-1" 
            aria-controls="messages-tabpanel-1" 
          />
        </Tabs>
      </Box>
      
      {/* Main content */}
      <Box sx={{ display: 'flex', mt: 2, height: 'calc(100vh - 180px)' }}>
        {/* Left panel - Dialog list */}
        <Box sx={{ width: 320, mr: 2 }}>
          <Box sx={{ mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Search dialogs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
              }}
            />
          </Box>
          
          <TabPanel value={tabValue} index={0}>
            {renderDialogList(filteredPendingResponses, true)}
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
            {renderDialogList(filteredHistoryResponses, false)}
          </TabPanel>
        </Box>
        
        {/* Right panel - Conversation view */}
        <Box sx={{ flexGrow: 1 }}>
          {renderConversationView()}
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
      
      {/* Auth Required Dialog */}
      <AuthRequiredDialog 
        open={showAuthDialog} 
        onClose={() => setShowAuthDialog(false)}
        action="view message responses"
      />
    </Box>
  );
};

export default Messages; 