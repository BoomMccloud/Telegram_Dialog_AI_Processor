import React, { useState } from 'react';
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
  Button,
  TextField,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
} from '@mui/material';
import { 
  Edit as EditIcon,
  Check as ApproveIcon,
  Close as RejectIcon,
  Send as SendIcon,
  Search as SearchIcon,
} from '@mui/icons-material';

interface Message {
  id: number;
  dialogName: string;
  suggestedResponse: string;
  editedResponse: string | null;
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'SENT' | 'FAILED';
  timestamp: string;
}

const Messages = () => {
  // Sample data - in a real app, this would come from an API
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      dialogName: 'John Doe',
      suggestedResponse: "I'll review the project timeline and get back to you tomorrow with an update.",
      editedResponse: null,
      status: 'PENDING_APPROVAL',
      timestamp: '2023-03-08T10:30:00Z',
    },
    {
      id: 2,
      dialogName: 'Marketing Group',
      suggestedResponse: "The Q2 metrics are looking good. I'll prepare a detailed analysis for our meeting.",
      editedResponse: "The Q2 metrics are positive. I'll bring a detailed analysis to our meeting next week.",
      status: 'APPROVED',
      timestamp: '2023-03-08T10:15:00Z',
    },
    {
      id: 3,
      dialogName: 'Support Team',
      suggestedResponse: "I've looked into the issue. It seems to be a configuration problem. Let me fix it.",
      editedResponse: null,
      status: 'SENT',
      timestamp: '2023-03-08T09:45:00Z',
    },
    {
      id: 4,
      dialogName: 'Product Team',
      suggestedResponse: 'The new feature implementation is on track for release next sprint.',
      editedResponse: null,
      status: 'FAILED',
      timestamp: '2023-03-08T09:15:00Z',
    },
  ]);

  // State for pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // State for the edit dialog
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [editedText, setEditedText] = useState('');

  // State for the filter
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Handle page change
  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Open edit dialog
  const handleOpenEditDialog = (message: Message) => {
    setSelectedMessage(message);
    setEditedText(message.editedResponse || message.suggestedResponse);
    setOpenEditDialog(true);
  };

  // Close edit dialog
  const handleCloseEditDialog = () => {
    setOpenEditDialog(false);
    setSelectedMessage(null);
  };

  // Save edited message
  const handleSaveEdit = () => {
    if (selectedMessage) {
      const updatedMessages = messages.map(message => 
        message.id === selectedMessage.id 
          ? { ...message, editedResponse: editedText, status: 'APPROVED' as const }
          : message
      );
      setMessages(updatedMessages);
      setOpenEditDialog(false);
      setSelectedMessage(null);
    }
  };

  // Approve message
  const handleApprove = (id: number) => {
    const updatedMessages = messages.map(message => 
      message.id === id 
        ? { ...message, status: 'APPROVED' as const }
        : message
    );
    setMessages(updatedMessages);
  };

  // Reject message
  const handleReject = (id: number) => {
    const updatedMessages = messages.map(message => 
      message.id === id 
        ? { ...message, status: 'REJECTED' as const }
        : message
    );
    setMessages(updatedMessages);
  };

  // Send message
  const handleSend = (id: number) => {
    const updatedMessages = messages.map(message => 
      message.id === id 
        ? { ...message, status: 'SENT' as const }
        : message
    );
    setMessages(updatedMessages);
  };

  // Get status chip color and label
  const getStatusChip = (status: Message['status']) => {
    switch (status) {
      case 'PENDING_APPROVAL':
        return <Chip label="Pending" color="warning" size="small" />;
      case 'APPROVED':
        return <Chip label="Approved" color="success" size="small" />;
      case 'REJECTED':
        return <Chip label="Rejected" color="error" size="small" />;
      case 'SENT':
        return <Chip label="Sent" color="info" size="small" />;
      case 'FAILED':
        return <Chip label="Failed" color="error" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
  };

  // Filter messages by status and search query
  const filteredMessages = messages.filter(message => 
    (statusFilter === 'all' || message.status === statusFilter) &&
    (searchQuery === '' || 
     message.dialogName.toLowerCase().includes(searchQuery.toLowerCase()) ||
     message.suggestedResponse.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Messages
      </Typography>
      
      {/* Filters and Search */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <TextField
          label="Search"
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
            <MenuItem value="PENDING_APPROVAL">Pending</MenuItem>
            <MenuItem value="APPROVED">Approved</MenuItem>
            <MenuItem value="REJECTED">Rejected</MenuItem>
            <MenuItem value="SENT">Sent</MenuItem>
            <MenuItem value="FAILED">Failed</MenuItem>
          </Select>
        </FormControl>
      </Box>
      
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
            {filteredMessages
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((message) => (
                <TableRow key={message.id}>
                  <TableCell component="th" scope="row">
                    {message.dialogName}
                  </TableCell>
                  <TableCell>
                    {message.editedResponse && message.status !== 'PENDING_APPROVAL'
                      ? message.editedResponse
                      : message.suggestedResponse}
                  </TableCell>
                  <TableCell>{getStatusChip(message.status)}</TableCell>
                  <TableCell>
                    {new Date(message.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                      {message.status === 'PENDING_APPROVAL' && (
                        <>
                          <Tooltip title="Approve">
                            <IconButton 
                              color="success" 
                              size="small"
                              onClick={() => handleApprove(message.id)}
                            >
                              <ApproveIcon />
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
                              <RejectIcon />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      
                      {message.status === 'APPROVED' && (
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
                      
                      {(message.status === 'SENT' || message.status === 'REJECTED' || message.status === 'FAILED') && (
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
        count={filteredMessages.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
      
      {/* Edit Dialog */}
      <Dialog 
        open={openEditDialog} 
        onClose={handleCloseEditDialog}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {selectedMessage?.status === 'PENDING_APPROVAL' ? 'Edit Response' : 'View Response'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Dialog with: {selectedMessage?.dialogName}
          </DialogContentText>
          
          <Typography variant="subtitle2" gutterBottom>
            AI Suggested Response:
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ p: 2, mb: 3, bgcolor: 'background.default' }}
          >
            <Typography>{selectedMessage?.suggestedResponse}</Typography>
          </Paper>
          
          <Typography variant="subtitle2" gutterBottom>
            {selectedMessage?.status === 'PENDING_APPROVAL' || selectedMessage?.status === 'APPROVED'
              ? 'Your Edited Response:'
              : 'Response:'}
          </Typography>
          
          {(selectedMessage?.status === 'PENDING_APPROVAL' || selectedMessage?.status === 'APPROVED') ? (
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
                {selectedMessage?.editedResponse || selectedMessage?.suggestedResponse}
              </Typography>
            </Paper>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEditDialog}>Cancel</Button>
          {(selectedMessage?.status === 'PENDING_APPROVAL' || selectedMessage?.status === 'APPROVED') && (
            <Button onClick={handleSaveEdit} variant="contained" color="primary">
              Save
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Messages; 