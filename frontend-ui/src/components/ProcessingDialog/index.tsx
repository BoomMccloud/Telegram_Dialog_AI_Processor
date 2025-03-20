import React from 'react';
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  LinearProgress,
  Alert,
} from '@mui/material';

// Progress tracking interface
export interface ProcessingProgress {
  totalDialogs: number;
  processedDialogs: number;
  currentDialogName: string;
  currentOperation: string;
  error: string | null;
}

// Progress dialog props interface
interface ProcessingDialogProps {
  open: boolean;
  progress: ProcessingProgress;
  onCancel: () => void;
}

// Processing dialog component
const ProcessingDialog: React.FC<ProcessingDialogProps> = ({ open, progress, onCancel }) => {
  return (
    <Dialog open={open} onClose={onCancel}>
      <DialogTitle>Processing Messages</DialogTitle>
      <DialogContent>
        <Box sx={{ width: '100%', mt: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {progress.currentOperation}
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Processing dialog: {progress.currentDialogName}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={(progress.processedDialogs / progress.totalDialogs) * 100} 
            sx={{ mt: 2, mb: 1 }}
          />
          <Typography variant="body2" color="text.secondary" align="center">
            {progress.processedDialogs} of {progress.totalDialogs} dialogs processed
          </Typography>
          {progress.error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {progress.error}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} color="primary">
          Cancel
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProcessingDialog; 