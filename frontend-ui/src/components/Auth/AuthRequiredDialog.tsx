import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogContentText, 
  DialogActions, 
  Button 
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

interface AuthRequiredDialogProps {
  open: boolean;
  onClose: () => void;
  action?: string;
}

const AuthRequiredDialog: React.FC<AuthRequiredDialogProps> = ({ 
  open, 
  onClose, 
  action = 'fetch Telegram dialogs'
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = () => {
    onClose();
    navigate('/login', { state: { from: location.pathname } });
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Authentication Required</DialogTitle>
      <DialogContent>
        <DialogContentText>
          You need to be logged in to {action}. Would you like to log in now?
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Cancel
        </Button>
        <Button onClick={handleLogin} color="primary" variant="contained">
          Log In
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AuthRequiredDialog; 