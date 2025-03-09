import React, { useState, useEffect, useCallback } from 'react';
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { 
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Person as PersonIcon,
  Group as GroupIcon,
  Campaign as ChannelIcon,
  Settings as SettingsIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';
import { Dialog as DialogType, SessionStatus } from '../../types';
import { checkAuthentication, initiateQRAuthentication, pollSessionStatus, devLogin } from '../../services/auth';
import AuthRequiredDialog from '../../components/Auth/AuthRequiredDialog';
import PhoneAuth from '../../components/Auth/PhoneAuth';

const Data = () => {
  // State for dialogs
  const [dialogs, setDialogs] = useState<DialogType[]>([]);
  
  // State for search
  const [searchQuery, setSearchQuery] = useState('');
  
  // State for loading indicators
  const [isLoading, setIsLoading] = useState(false);
  const [isPollingSession, setIsPollingSession] = useState(false);
  
  // State for authentication
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  
  // State for QR code dialog
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [qrCode, setQrCode] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [qrSessionError, setQrSessionError] = useState(false);
  
  // Add state for authentication required dialog
  const [authDialogOpen, setAuthDialogOpen] = useState(false);
  
  // Add state for phone authentication
  const [phoneDialogOpen, setPhoneDialogOpen] = useState<boolean>(false);
  
  // Fetch dialog list from backend
  const fetchDialogs = useCallback(async () => {
    try {
      setIsLoading(true);
      setAuthError(null);
      
      // Try to fetch dialogs
      const response = await api.telegram.getDialogs();
      setDialogs(response.dialogs);
      
      // If we succeeded, update isAuthenticated state
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Failed to fetch dialogs:', error);
      
      // Check if the error is due to authentication required
      if (error instanceof Error && error.message === 'AUTH_REQUIRED') {
        // Show authentication required dialog
        setAuthDialogOpen(true);
      } else {
        setAuthError('Failed to fetch Telegram dialogs. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  // Handle phone authentication success
  const handlePhoneAuthSuccess = () => {
    console.log('[UI Debug] Phone authentication successful');
    
    // Check if we have the access token before proceeding
    const accessToken = localStorage.getItem('accessToken');
    if (!accessToken) {
      console.warn('[UI Debug] No access token found after authentication, checking session');
      
      // Try to verify the session to get tokens
      api.auth.verifySession()
        .then(response => {
          if (response.status === SessionStatus.AUTHENTICATED) {
            console.log('[UI Debug] Session verified after phone auth');
            setIsAuthenticated(true);
            setPhoneDialogOpen(false);
            // Now try to fetch dialogs
            fetchDialogs();
          } else {
            setAuthError('Authentication successful but session could not be verified. Please try again.');
            setPhoneDialogOpen(false);
          }
        })
        .catch(error => {
          console.error('[UI Debug] Failed to verify session after phone auth:', error);
          setAuthError('Authentication successful but session could not be verified. Please try again.');
          setPhoneDialogOpen(false);
        });
    } else {
      // We have the token, proceed normally
      setIsAuthenticated(true);
      setPhoneDialogOpen(false);
      fetchDialogs();
    }
  };
  
  // Handle authenticate button click - now defaults to phone auth
  const handleAuthenticateClick = () => {
    setPhoneDialogOpen(true);
  };
  
  // Initialize QR authentication - kept as an alternative
  const handleQRAuthenticate = async () => {
    setIsLoading(true);
    setAuthError(null);
    setQrSessionError(false);
    
    console.log('[UI Debug] Starting QR authentication process...');
    
    try {
      const response = await initiateQRAuthentication();
      console.log('[UI Debug] QR code generated successfully', { 
        session_id: response.session_id,
        expires_at: response.expires_at
      });
      
      setQrCode(response.qr_code);
      localStorage.setItem('tempSessionId', response.session_id);
      setExpiresAt(response.expires_at);
      setQrDialogOpen(true);
      
      // Start polling for session status
      setIsPollingSession(true);
      
      // Use the new polling function
      pollSessionStatus(
        (status, error) => {
          console.log(`[UI Debug] Session status update: ${status}`, { error });
          
          if (status === SessionStatus.AUTHENTICATED) {
            console.log('[UI Debug] Authentication successful, updating UI');
            setIsAuthenticated(true);
            setIsPollingSession(false);
            setQrDialogOpen(false);
            fetchDialogs();
          } else if (status === SessionStatus.ERROR || status === SessionStatus.EXPIRED) {
            console.log('[UI Debug] Authentication failed or expired');
            setQrSessionError(true);
            setIsPollingSession(false);
            if (error) {
              setAuthError(`Authentication error: ${error.message}`);
            }
          }
        }
      );
    } catch (error) {
      console.error('[UI Debug] Failed to create QR authentication:', error);
      setAuthError('Failed to create authentication session. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Logout
  const handleLogout = async () => {
    setIsLoading(true);
    
    try {
      await api.auth.logout();
      setIsAuthenticated(false);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setDialogs([]);
    } catch (error) {
      console.error('Failed to logout:', error);
      setAuthError('Failed to logout. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
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

  // Refresh dialogs from Telegram
  const handleRefreshDialogs = () => {
    fetchDialogs();
  };

  // Get appropriate icon for dialog type
  const getDialogIcon = (type: DialogType['type']) => {
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
  const getDialogTypeChip = (type: DialogType['type']) => {
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
  
  // Check for existing authentication tokens on component mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      setIsLoading(true);
      try {
        const isAuth = await checkAuthentication();
        setIsAuthenticated(isAuth);
        // We don't automatically fetch dialogs anymore, even if authenticated
      } catch (error) {
        console.error('Error checking authentication status:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuthStatus();
  }, []);  // Remove fetchDialogs from dependency array
  
  // Filter dialogs by search query
  const filteredDialogs = dialogs.filter(dialog => 
    dialog.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Test if a token is valid
  const testToken = async (token: string) => {
    try {
      console.log(`[UI Debug] Testing token: ${token.substring(0, 10)}...`);
      
      // Make a direct fetch call to avoid interceptors
      const response = await fetch('http://localhost:8000/api/auth/session/verify', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('[UI Debug] Token is valid:', data);
        alert(`Token is valid! Status: ${data.status}`);
        return true;
      } else {
        const errorText = await response.text();
        console.error('[UI Debug] Token validation failed:', response.status, errorText);
        alert(`Token validation failed: ${response.status} ${errorText}`);
        return false;
      }
    } catch (error: unknown) {
      console.error('[UI Debug] Token test error:', error);
      alert(`Error testing token: ${error instanceof Error ? error.message : String(error)}`);
      return false;
    }
  };

  // Direct API call to dev login
  const directDevLogin = async (telegramId: number) => {
    try {
      console.log(`[UI Debug] Making direct dev login call with ID: ${telegramId}`);
      
      const response = await fetch('http://localhost:8000/api/auth/dev-login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ telegram_id: telegramId })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('[UI Debug] Direct dev login successful:', data);
        
        // Store the token
        if (data.token) {
          localStorage.setItem('accessToken', data.token);
          alert(`Login successful! Token: ${data.token.substring(0, 15)}...`);
          
          // Test the token immediately
          await testToken(data.token);
          
          setIsAuthenticated(true);
          setQrDialogOpen(false);
          fetchDialogs();
          return true;
        } else {
          alert('Login response did not contain a token');
          return false;
        }
      } else {
        const errorText = await response.text();
        console.error('[UI Debug] Direct dev login failed:', response.status, errorText);
        alert(`Login failed: ${response.status} ${errorText}`);
        return false;
      }
    } catch (error: unknown) {
      console.error('[UI Debug] Direct dev login error:', error);
      alert(`Error during login: ${error instanceof Error ? error.message : String(error)}`);
      return false;
    }
  };

  // QR Code Authentication Dialog
  const renderQrDialog = () => (
    <Dialog open={qrDialogOpen} onClose={() => {
      setQrDialogOpen(false);
      setIsPollingSession(false);
    }}>
      <DialogTitle>Authenticate with Telegram</DialogTitle>
      <DialogContent>
        <Box sx={{ textAlign: 'center', p: 2 }}>
          <Typography variant="body1" paragraph>
            Scan this QR code with your Telegram app to authenticate:
          </Typography>
          
          {qrCode && (
            <img
              src={`data:image/png;base64,${qrCode}`}
              alt="QR Code for Telegram authentication"
              style={{ maxWidth: '100%', height: 'auto' }}
            />
          )}
          
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
            Session expires: {new Date(expiresAt).toLocaleString()}
          </Typography>
          
          {isPollingSession && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 2 }}>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography variant="body2">
                {qrSessionError 
                  ? "Waiting for scan... (Having trouble connecting to server)" 
                  : "Waiting for authentication..."}
              </Typography>
            </Box>
          )}
          
          {qrSessionError && (
            <Alert severity="info" sx={{ mt: 2, textAlign: 'left' }}>
              Tip: Open Telegram on your mobile device, go to Settings → Devices → Scan QR Code
            </Alert>
          )}
          
          {/* Debug Tools */}
          <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid #eee' }}>
            <Typography variant="overline" color="text.secondary">
              Debug Options
            </Typography>
            
            <Box sx={{ mt: 1 }}>
              <Button 
                variant="outlined" 
                size="small" 
                color="secondary" 
                onClick={() => {
                  console.log('[DEBUG] Checking session status manually');
                  api.auth.verifySession()
                    .then(response => {
                      console.log('[DEBUG] Manual session check:', response);
                      alert(`Session status: ${response.status}\nUser: ${response.user ? response.user.username : 'none'}`);
                    })
                    .catch(err => {
                      console.error('[DEBUG] Manual session check failed:', err);
                      alert(`Session check failed: ${err.message}`);
                    });
                }}
              >
                Check Session
              </Button>
              
              <Button 
                variant="outlined" 
                size="small" 
                color="warning" 
                sx={{ ml: 1 }}
                onClick={() => {
                  // Try to simulate authentication for testing
                  const fakeToken = prompt('Enter a test token to simulate authentication:');
                  if (fakeToken) {
                    localStorage.setItem('accessToken', fakeToken);
                    alert('Token saved! Testing authentication...');
                    setIsAuthenticated(true);
                    setQrDialogOpen(false);
                    fetchDialogs();
                  }
                }}
              >
                Test Auth
              </Button>
              
              <Button 
                variant="outlined" 
                size="small" 
                color="error" 
                sx={{ ml: 1 }}
                onClick={async () => {
                  const telegramId = prompt('Enter a Telegram ID for dev login:');
                  if (telegramId && !isNaN(Number(telegramId))) {
                    const id = Number(telegramId);
                    const success = await devLogin(id);
                    
                    if (success) {
                      alert(`Dev login successful with ID ${id}`);
                      setIsAuthenticated(true);
                      setQrDialogOpen(false);
                      fetchDialogs();
                    } else {
                      alert('Dev login failed. Check console for details.');
                    }
                  } else {
                    alert('Please enter a valid numeric Telegram ID');
                  }
                }}
              >
                Dev Login
              </Button>
              
              <Button 
                variant="outlined" 
                size="small" 
                color="info" 
                sx={{ ml: 1, mt: 1 }}
                onClick={() => {
                  const token = localStorage.getItem('accessToken');
                  if (token) {
                    testToken(token);
                  } else {
                    alert('No token found in localStorage');
                  }
                }}
              >
                Test Current Token
              </Button>
              
              <Button 
                variant="outlined" 
                size="small" 
                color="success" 
                sx={{ ml: 1, mt: 1 }}
                onClick={async () => {
                  const telegramId = prompt('Enter a Telegram ID for direct dev login:');
                  if (telegramId && !isNaN(Number(telegramId))) {
                    await directDevLogin(Number(telegramId));
                  } else {
                    alert('Please enter a valid numeric Telegram ID');
                  }
                }}
              >
                Direct Dev Login
              </Button>
            </Box>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button 
          onClick={() => {
            setQrDialogOpen(false);
            setIsPollingSession(false);
          }}
        >
          Close
        </Button>
        <Button 
          color="primary"
          onClick={handleQRAuthenticate} 
          disabled={isLoading}
        >
          Refresh QR Code
        </Button>
      </DialogActions>
    </Dialog>
  );

  // Phone Authentication Dialog
  const renderPhoneDialog = () => (
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
            onSwitchToQR={() => {
              setPhoneDialogOpen(false);
              handleQRAuthenticate();
            }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Telegram Dialogs
      </Typography>
      
      {authError && (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          onClose={() => setAuthError(null)}
        >
          {authError}
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
          {isAuthenticated ? (
            <>
              <Button 
                variant="contained" 
                startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
                onClick={handleRefreshDialogs}
                disabled={isLoading}
                sx={{ mr: 1 }}
              >
                Refresh
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<LogoutIcon />}
                onClick={handleLogout}
                disabled={isLoading}
              >
                Logout
              </Button>
            </>
          ) : (
            <Button
              variant="contained"
              color="primary"
              startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <LoginIcon />}
              onClick={handleAuthenticateClick}
              disabled={isLoading}
            >
              Authenticate
            </Button>
          )}
        </Box>
        
        <Typography variant="body2" color="text.secondary">
          {isAuthenticated 
            ? "Select which Telegram dialogs you want to process with AI responses." 
            : "Please authenticate with Telegram to manage your dialogs."}
        </Typography>
      </Paper>
      
      {isAuthenticated && (
        <Paper elevation={2}>
          {filteredDialogs.length > 0 ? (
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
                          <Typography variant="body1" sx={{ mr: 1 }}>
                            {dialog.name}
                          </Typography>
                          {dialog.unread_count > 0 && (
                            <Chip 
                              label={dialog.unread_count} 
                              size="small" 
                              color="primary" 
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                          {getDialogTypeChip(dialog.type)}
                          <Typography variant="caption" sx={{ ml: 1 }}>
                            ID: {dialog.telegram_dialog_id}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              {isLoading ? (
                <CircularProgress />
              ) : (
                <Typography variant="body1" color="text.secondary">
                  No dialogs found. Click refresh to fetch your Telegram dialogs.
                </Typography>
              )}
            </Box>
          )}
        </Paper>
      )}
      
      {renderQrDialog()}
      {renderPhoneDialog()}
      
      {/* Authentication Required Dialog */}
      <AuthRequiredDialog 
        open={authDialogOpen} 
        onClose={() => setAuthDialogOpen(false)} 
        action="access your Telegram dialogs"
      />
    </Box>
  );
};

export default Data; 