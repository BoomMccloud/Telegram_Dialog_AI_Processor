import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
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
  Tooltip,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import HistoryIcon from '@mui/icons-material/History';
import PendingIcon from '@mui/icons-material/Pending';
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

const Messages = () => {
  // Tab state
  const [tabValue, setTabValue] = useState(0);
  
  // State for messages
  const [pendingMessages, setPendingMessages] = useState<Response[]>([]);
  const [historyMessages, setHistoryMessages] = useState<Response[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalPendingMessages, setTotalPendingMessages] = useState(0);
  const [totalHistoryMessages, setTotalHistoryMessages] = useState(0);
  
  // Pagination state
  const [pendingPage, setPendingPage] = useState(0);
  const [historyPage, setHistoryPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // Edit dialog state
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<Response | null>(null);
  const [editedText, setEditedText] = useState('');
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Auth required dialog
  const [showAuthDialog, setShowAuthDialog] = useState(false);

  // Handle tab change
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Reset search when switching tabs
    setSearchQuery('');
  };

  // Fetch messages on component mount and when filters change
  useEffect(() => {
    if (tabValue === 0) {
      fetchPendingMessages();
    } else {
      fetchHistoryMessages();
    }
  }, [tabValue, pendingPage, historyPage, rowsPerPage, statusFilter]);

  // Function to fetch pending messages from API
  const fetchPendingMessages = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getPending(pendingPage * rowsPerPage, rowsPerPage);
      setPendingMessages(response.responses);
      setTotalPendingMessages(response.total);
    } catch (err: unknown) {
      console.error('Error fetching pending messages:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setShowAuthDialog(true);
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setShowAuthDialog(true);
      } else {
        setError('Failed to load pending messages. Please try again later.');
      }
      
      setPendingMessages([]);
      setTotalPendingMessages(0);
    } finally {
      setLoading(false);
    }
  };

  // Function to fetch history messages from API
  const fetchHistoryMessages = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getHistory(
        historyPage * rowsPerPage, 
        rowsPerPage, 
        statusFilter !== 'all' ? statusFilter : undefined
      );
      
      setHistoryMessages(response.responses);
      setTotalHistoryMessages(response.total);
    } catch (err: unknown) {
      console.error('Error fetching history messages:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setShowAuthDialog(true);
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setShowAuthDialog(true);
      } else {
        setError('Failed to load message history. Please try again later.');
      }
      
      setHistoryMessages([]);
      setTotalHistoryMessages(0);
    } finally {
      setLoading(false);
    }
  };

  // Refresh current view
  const refreshCurrentView = () => {
    if (tabValue === 0) {
      fetchPendingMessages();
    } else {
      fetchHistoryMessages();
    }
  };

  // Handle page change for pending messages
  const handlePendingPageChange = (_event: unknown, newPage: number) => {
    setPendingPage(newPage);
  };

  // Handle page change for history messages
  const handleHistoryPageChange = (_event: unknown, newPage: number) => {
    setHistoryPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPendingPage(0);
    setHistoryPage(0);
  };

  // Open edit dialog
  const handleOpenEditDialog = (message: Response) => {
    setSelectedMessage(message);
    setEditedText(message.edited_response || message.suggested_response);
    setOpenEditDialog(true);
  };

  // Close edit dialog
  const handleCloseEditDialog = () => {
    setOpenEditDialog(false);
    setSelectedMessage(null);
    setEditedText('');
  };

  // Save edited response
  const handleSaveEdit = async () => {
    if (!selectedMessage) return;
    
    try {
      await api.responses.update(selectedMessage.id, { edited_response: editedText });
      refreshCurrentView(); // Refresh messages after update
      handleCloseEditDialog();
    } catch (err) {
      console.error('Error updating response:', err);
      setError('Failed to update response. Please try again.');
    }
  };

  // Approve response
  const handleApprove = async (id: string) => {
    try {
      await api.responses.approve(id);
      refreshCurrentView(); // Refresh messages after approval
    } catch (err) {
      console.error('Error approving response:', err);
      setError('Failed to approve response. Please try again.');
    }
  };

  // Reject response
  const handleReject = async (id: string) => {
    try {
      await api.responses.reject(id);
      refreshCurrentView(); // Refresh messages after rejection
    } catch (err) {
      console.error('Error rejecting response:', err);
      setError('Failed to reject response. Please try again.');
    }
  };

  // Send response
  const handleSend = async (id: string) => {
    try {
      await api.responses.send(id);
      refreshCurrentView(); // Refresh messages after sending
    } catch (err) {
      console.error('Error sending response:', err);
      setError('Failed to send response. Please try again.');
    }
  };

  // Filter messages by search query
  const filteredPendingMessages = pendingMessages.filter(message => 
    message.dialog_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    message.suggested_response.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (message.edited_response && message.edited_response.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const filteredHistoryMessages = historyMessages.filter(message => 
    message.dialog_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    message.suggested_response.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (message.edited_response && message.edited_response.toLowerCase().includes(searchQuery.toLowerCase()))
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

  // Render message table
  const renderMessageTable = (messages: Response[], isPending: boolean) => (
    <TableContainer component={Paper} sx={{ mt: 2 }}>
      <Table size="medium">
        <TableHead>
          <TableRow>
            <TableCell>Dialog</TableCell>
            <TableCell>Suggested Response</TableCell>
            {!isPending && <TableCell>Status</TableCell>}
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {messages.length === 0 ? (
            <TableRow>
              <TableCell colSpan={isPending ? 3 : 4} align="center">
                {loading ? (
                  <CircularProgress size={24} />
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    {isPending 
                      ? "No pending responses found. All caught up!" 
                      : "No response history found."}
                  </Typography>
                )}
              </TableCell>
            </TableRow>
          ) : (
            messages.map((message) => (
              <TableRow key={message.id}>
                <TableCell>{message.dialog_name}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ maxWidth: 300, whiteSpace: 'pre-wrap' }}>
                    {message.edited_response || message.suggested_response}
                  </Typography>
                </TableCell>
                {!isPending && <TableCell>{getStatusChip(message.status)}</TableCell>}
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {isPending && (
                      <>
                        <Tooltip title="Approve">
                          <IconButton 
                            size="small" 
                            color="success" 
                            onClick={() => handleApprove(message.id)}
                          >
                            <CheckCircleIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Reject">
                          <IconButton 
                            size="small" 
                            color="error" 
                            onClick={() => handleReject(message.id)}
                          >
                            <CancelIcon />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                    <Tooltip title="Edit">
                      <IconButton 
                        size="small" 
                        color="primary" 
                        onClick={() => handleOpenEditDialog(message)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    {message.status === ResponseStatus.APPROVED && (
                      <Tooltip title="Send">
                        <IconButton 
                          size="small" 
                          color="primary" 
                          onClick={() => handleSend(message.id)}
                        >
                          <SendIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

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
            label="Pending Responses" 
            id="messages-tab-0" 
            aria-controls="messages-tabpanel-0" 
          />
          <Tab 
            icon={<HistoryIcon />} 
            iconPosition="start" 
            label="Response History" 
            id="messages-tab-1" 
            aria-controls="messages-tabpanel-1" 
          />
        </Tabs>
      </Box>
      
      {/* Pending Responses Tab */}
      <TabPanel value={tabValue} index={0}>
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <TextField
            label="Search"
            placeholder="Search by dialog or content"
            variant="outlined"
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ minWidth: 200 }}
            InputProps={{
              endAdornment: <SearchIcon color="action" />,
            }}
          />
          
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchPendingMessages}
          >
            Refresh
          </Button>
        </Box>
        
        {renderMessageTable(filteredPendingMessages, true)}
        
        <TablePagination
          component="div"
          count={totalPendingMessages}
          page={pendingPage}
          onPageChange={handlePendingPageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </TabPanel>
      
      {/* Response History Tab */}
      <TabPanel value={tabValue} index={1}>
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <TextField
            label="Search"
            placeholder="Search by dialog or content"
            variant="outlined"
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ minWidth: 200 }}
            InputProps={{
              endAdornment: <SearchIcon color="action" />,
            }}
          />
          
          <FormControl size="small" sx={{ minWidth: 150 }}>
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
          
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchHistoryMessages}
          >
            Refresh
          </Button>
        </Box>
        
        {renderMessageTable(filteredHistoryMessages, false)}
        
        <TablePagination
          component="div"
          count={totalHistoryMessages}
          page={historyPage}
          onPageChange={handleHistoryPageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </TabPanel>
      
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