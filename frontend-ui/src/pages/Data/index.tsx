import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  List, 
  ListItem, 
  ListItemText,
  ListItemAvatar,
  Avatar,
  Switch,
  Chip,
  Divider,
  Button,
  TextField,
  InputAdornment,
  FormControlLabel,
  Alert,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import { 
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Campaign as ChannelIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

// Define Dialog interface
interface Dialog {
  id: number;
  telegram_dialog_id: string;
  name: string;
  unread_count: number;
  type: 'PRIVATE' | 'GROUP' | 'CHANNEL';
  is_processing_enabled: boolean;
  auto_send_enabled: boolean;
}

const Data = () => {
  // Sample data - in a real app, this would come from an API
  const [dialogs, setDialogs] = useState<Dialog[]>([
    {
      id: 1,
      telegram_dialog_id: '123456789',
      name: 'John Doe',
      unread_count: 5,
      type: 'PRIVATE',
      is_processing_enabled: true,
      auto_send_enabled: false,
    },
    {
      id: 2,
      telegram_dialog_id: '987654321',
      name: 'Marketing Team',
      unread_count: 10,
      type: 'GROUP',
      is_processing_enabled: true,
      auto_send_enabled: true,
    },
    {
      id: 3,
      telegram_dialog_id: '456123789',
      name: 'Company Announcements',
      unread_count: 0,
      type: 'CHANNEL',
      is_processing_enabled: false,
      auto_send_enabled: false,
    },
    {
      id: 4,
      telegram_dialog_id: '789456123',
      name: 'Support Chat',
      unread_count: 3,
      type: 'GROUP',
      is_processing_enabled: false,
      auto_send_enabled: false,
    },
  ]);

  // State for search
  const [searchQuery, setSearchQuery] = useState('');
  
  // State for loading indicator
  const [isLoading, setIsLoading] = useState(false);
  
  // State for authentication reminder
  const [needsAuth, setNeedsAuth] = useState(false);

  // Toggle processing for dialog
  const handleToggleProcessing = (id: number) => {
    setDialogs(prevDialogs => 
      prevDialogs.map(dialog => 
        dialog.id === id
          ? { ...dialog, is_processing_enabled: !dialog.is_processing_enabled }
          : dialog
      )
    );
  };

  // Toggle auto-send for dialog
  const handleToggleAutoSend = (id: number) => {
    setDialogs(prevDialogs => 
      prevDialogs.map(dialog => 
        dialog.id === id
          ? { ...dialog, auto_send_enabled: !dialog.auto_send_enabled }
          : dialog
      )
    );
  };

  // Mock refreshing dialogs from Telegram
  const handleRefreshDialogs = () => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      setNeedsAuth(Math.random() > 0.7); // Randomly show auth reminder for demo
    }, 1000);
  };

  // Get appropriate icon for dialog type
  const getDialogIcon = (type: Dialog['type']) => {
    switch (type) {
      case 'PRIVATE':
        return <PersonIcon />;
      case 'GROUP':
        return <GroupIcon />;
      case 'CHANNEL':
        return <ChannelIcon />;
      default:
        return <PersonIcon />;
    }
  };

  // Get appropriate chip for dialog type
  const getDialogTypeChip = (type: Dialog['type']) => {
    switch (type) {
      case 'PRIVATE':
        return <Chip label="Private" size="small" color="primary" variant="outlined" />;
      case 'GROUP':
        return <Chip label="Group" size="small" color="success" variant="outlined" />;
      case 'CHANNEL':
        return <Chip label="Channel" size="small" color="info" variant="outlined" />;
      default:
        return <Chip label={type} size="small" variant="outlined" />;
    }
  };

  // Filter dialogs by search query
  const filteredDialogs = dialogs.filter(dialog => 
    dialog.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Telegram Dialogs
      </Typography>
      
      {needsAuth && (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small">
              Authenticate
            </Button>
          }
        >
          Your Telegram authentication has expired. Please authenticate to continue.
        </Alert>
      )}
      
      <Paper sx={{ mb: 3, p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <TextField
            placeholder="Search dialogs"
            variant="outlined"
            size="small"
            sx={{ flexGrow: 1, mr: 2 }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
          />
          <Button 
            variant="contained" 
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
            onClick={handleRefreshDialogs}
            disabled={isLoading}
          >
            Refresh
          </Button>
        </Box>
        
        <Typography variant="body2" color="text.secondary">
          Select which Telegram dialogs you want to process with AI responses.
        </Typography>
      </Paper>
      
      <Paper elevation={2}>
        <List>
          {filteredDialogs.map((dialog, index) => (
            <React.Fragment key={dialog.id}>
              {index > 0 && <Divider />}
              <ListItem
                secondaryAction={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dialog.auto_send_enabled}
                          onChange={() => handleToggleAutoSend(dialog.id)}
                          disabled={!dialog.is_processing_enabled}
                        />
                      }
                      label="Auto-send"
                      labelPlacement="start"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dialog.is_processing_enabled}
                          onChange={() => handleToggleProcessing(dialog.id)}
                        />
                      }
                      label="Process"
                      labelPlacement="start"
                    />
                    <Tooltip title="Settings">
                      <IconButton edge="end" aria-label="settings">
                        <SettingsIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                }
              >
                <ListItemAvatar>
                  <Avatar>
                    {getDialogIcon(dialog.type)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Typography variant="subtitle1" component="span">
                        {dialog.name}
                      </Typography>
                      {dialog.unread_count > 0 && (
                        <Chip 
                          label={dialog.unread_count} 
                          size="small" 
                          color="primary" 
                          sx={{ ml: 1 }} 
                        />
                      )}
                      <Box sx={{ ml: 'auto', mr: 2 }}>
                        {getDialogTypeChip(dialog.type)}
                      </Box>
                    </Box>
                  }
                  secondary={`ID: ${dialog.telegram_dialog_id}`}
                />
              </ListItem>
            </React.Fragment>
          ))}
          {filteredDialogs.length === 0 && (
            <ListItem>
              <ListItemText 
                primary="No dialogs found" 
                secondary={searchQuery ? "Try a different search term" : "Refresh to load dialogs"} 
              />
            </ListItem>
          )}
        </List>
      </Paper>
    </Box>
  );
};

export default Data; 