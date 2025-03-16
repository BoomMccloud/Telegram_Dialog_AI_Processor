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
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import AuthRequiredDialog from '../../components/Auth/AuthRequiredDialog';
import { api } from '../../services/api';
import { Response, ResponseStatus } from '../../types';

const Messages = () => {
  // State for messages
  const [messages, setMessages] = useState<Response[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalMessages, setTotalMessages] = useState(0);
  
  // Pagination state
  const [page, setPage] = useState(0);
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

  // Fetch messages on component mount and when filters change
  useEffect(() => {
    fetchMessages();
  }, [page, rowsPerPage, statusFilter]);

  // Function to fetch messages from API
  const fetchMessages = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let response;
      
      if (statusFilter === 'pending_approval') {
        response = await api.responses.getPending(page * rowsPerPage, rowsPerPage);
      } else {
        response = await api.responses.getHistory(
          page * rowsPerPage, 
          rowsPerPage, 
          statusFilter !== 'all' ? statusFilter : undefined
        );
      }
      
      setMessages(response.responses);
      setTotalMessages(response.total);
    } catch (err: unknown) {
      console.error('Error fetching messages:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setShowAuthDialog(true);
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setShowAuthDialog(true);
      } else {
        setError('Failed to load messages. Please try again later.');
      }
      
      setMessages([]);
      setTotalMessages(0);
    } finally {
      setLoading(false);
    }
  };

  // Handle page change
  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
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
      fetchMessages(); // Refresh messages after update
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
      fetchMessages(); // Refresh messages after approval
    } catch (err) {
      console.error('Error approving response:', err);
      setError('Failed to approve response. Please try again.');
    }
  };

  // Reject response
  const handleReject = async (id: string) => {
    try {
      await api.responses.reject(id);
      fetchMessages(); // Refresh messages after rejection
    } catch (err) {
      console.error('Error rejecting response:', err);
      setError('Failed to reject response. Please try again.');
    }
  };

  // Send response
  const handleSend = async (id: string) => {
    try {
      await api.responses.send(id);
      fetchMessages(); // Refresh messages after sending
    } catch (err) {
      console.error('Error sending response:', err);
      setError('Failed to send response. Please try again.');
    }
  };

  // Filter messages by search query
  const filteredMessages = messages.filter(message => 
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
      
      {/* Filters */}
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
            <MenuItem value="pending_approval">Pending</MenuItem>
            <MenuItem value="approved">Approved</MenuItem>
            <MenuItem value="rejected">Rejected</MenuItem>
            <MenuItem value="sent">Sent</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </Select>
        </FormControl>
        
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchMessages}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>
      
      {/* Loading indicator */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : messages.length === 0 ? (
        <Alert severity="info">
          No messages found. {statusFilter !== 'all' ? 'Try changing the status filter.' : ''}
        </Alert>
      ) : (
        <>
          {/* Messages Table */}
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="messages table">
              <TableHead>
                <TableRow>
                  <TableCell>Dialog</TableCell>
                  <TableCell>Response</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Timestamp</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredMessages.map((message) => (
                  <TableRow key={message.id}>
                    <TableCell component="th" scope="row">
                      {message.dialog_name}
                    </TableCell>
                    <TableCell>
                      {message.edited_response && message.status !== ResponseStatus.PENDING_APPROVAL
                        ? message.edited_response
                        : message.suggested_response}
                    </TableCell>
                    <TableCell>{getStatusChip(message.status)}</TableCell>
                    <TableCell>
                      {new Date(message.processed_at).toLocaleString()}
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                        {message.status === ResponseStatus.PENDING_APPROVAL && (
                          <>
                            <Tooltip title="Approve">
                              <IconButton 
                                color="success" 
                                size="small"
                                onClick={() => handleApprove(message.id)}
                              >
                                <CheckCircleIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Edit">
                              <IconButton 
                                color="primary" 
                                size="small"
                                onClick={() => handleOpenEditDialog(message)}
                              >
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Reject">
                              <IconButton 
                                color="error" 
                                size="small"
                                onClick={() => handleReject(message.id)}
                              >
                                <CancelIcon />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        
                        {message.status === ResponseStatus.APPROVED && (
                          <>
                            <Tooltip title="Edit">
                              <IconButton 
                                color="primary" 
                                size="small"
                                onClick={() => handleOpenEditDialog(message)}
                              >
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Send">
                              <IconButton 
                                color="info" 
                                size="small"
                                onClick={() => handleSend(message.id)}
                              >
                                <SendIcon />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        
                        {(message.status === ResponseStatus.SENT || 
                          message.status === ResponseStatus.REJECTED || 
                          message.status === ResponseStatus.FAILED) && (
                          <>
                            <Tooltip title="View">
                              <IconButton 
                                color="primary" 
                                size="small"
                                onClick={() => handleOpenEditDialog(message)}
                              >
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          <TablePagination
            rowsPerPageOptions={[5, 10, 25]}
            component="div"
            count={totalMessages}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
          />
        </>
      )}
      
      {/* Edit Dialog */}
      <Dialog 
        open={openEditDialog} 
        onClose={handleCloseEditDialog}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {selectedMessage?.status === ResponseStatus.PENDING_APPROVAL ? 'Edit Response' : 'View Response'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Dialog with: {selectedMessage?.dialog_name}
          </DialogContentText>
          
          <Typography variant="subtitle2" gutterBottom>
            AI Suggested Response:
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}
          >
            <Typography>{selectedMessage?.suggested_response}</Typography>
          </Paper>
          
          <Typography variant="subtitle2" gutterBottom>
            {selectedMessage?.status === ResponseStatus.PENDING_APPROVAL || selectedMessage?.status === ResponseStatus.APPROVED
              ? 'Your Edited Response:'
              : 'Response:'}
          </Typography>
          
          {(selectedMessage?.status === ResponseStatus.PENDING_APPROVAL || selectedMessage?.status === ResponseStatus.APPROVED) ? (
            <TextField
              fullWidth
              multiline
              rows={4}
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              variant="outlined"
            />
          ) : (
            <Paper 
              variant="outlined" 
              sx={{ p: 2, bgcolor: 'background.default' }}
            >
              <Typography>
                {selectedMessage?.edited_response || selectedMessage?.suggested_response}
              </Typography>
            </Paper>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog}>Cancel</Button>
          {(selectedMessage?.status === ResponseStatus.PENDING_APPROVAL || selectedMessage?.status === ResponseStatus.APPROVED) && (
            <Button onClick={handleSaveEdit} variant="contained" color="primary">
              Save
            </Button>
          )}
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