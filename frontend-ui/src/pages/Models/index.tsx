import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  TextField, 
  Button, 
  Alert,
  Grid,
  Chip,
  CircularProgress,
  Snackbar,
  SelectChangeEvent,
} from '@mui/material';
import { 
  Save as SaveIcon,
} from '@mui/icons-material';

// Define available models
interface Model {
  id: string;
  name: string;
  description: string;
  isAvailable: boolean;
}

const Models = () => {
  // Available models - in a real app, this would come from an API
  const availableModels: Model[] = [
    {
      id: 'gpt-4',
      name: 'GPT-4',
      description: 'Most capable model, best for complex tasks requiring deep understanding.',
      isAvailable: true,
    },
    {
      id: 'gpt-3.5-turbo',
      name: 'GPT-3.5 Turbo',
      description: 'Faster response times, good balance between capabilities and speed.',
      isAvailable: true,
    },
    {
      id: 'claude-3',
      name: 'Claude 3',
      description: 'Well-balanced model with good reasoning capabilities.',
      isAvailable: true,
    },
    {
      id: 'llama-3',
      name: 'Llama 3',
      description: 'Open-source model, runs locally for better privacy.',
      isAvailable: false, // Example of an unavailable model
    },
  ];

  // State for selected model
  const [selectedModelId, setSelectedModelId] = useState('gpt-4');
  
  // State for system prompt
  const [systemPrompt, setSystemPrompt] = useState(
    `You are an AI assistant helping to craft responses to Telegram messages. 
Your task is to generate thoughtful, helpful replies that sound natural and match the user's writing style.

Instructions:
1. Maintain the same tone and level of formality as the original conversation
2. Keep responses concise and to the point
3. Address all questions or points raised in the messages
4. Be helpful but not overly enthusiastic
5. Never mention that you are an AI or that this message is being processed automatically`
  );
  
  // State for saving indicator
  const [isSaving, setIsSaving] = useState(false);
  
  // State for success notification
  const [showSuccess, setShowSuccess] = useState(false);

  // Handle model change
  const handleModelChange = (event: SelectChangeEvent) => {
    setSelectedModelId(event.target.value);
  };

  // Handle saving settings
  const handleSaveSettings = () => {
    setIsSaving(true);
    // Simulate API call
    setTimeout(() => {
      setIsSaving(false);
      setShowSuccess(true);
    }, 1000);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        AI Model Configuration
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Select Model
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Choose which AI model to use for processing Telegram messages.
            </Typography>
            
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel id="model-select-label">AI Model</InputLabel>
              <Select
                labelId="model-select-label"
                value={selectedModelId}
                label="AI Model"
                onChange={handleModelChange}
              >
                {availableModels.map((model) => (
                  <MenuItem 
                    key={model.id} 
                    value={model.id}
                    disabled={!model.isAvailable}
                  >
                    {model.name}
                    {!model.isAvailable && (
                      <Chip 
                        label="Unavailable" 
                        size="small" 
                        color="default" 
                        sx={{ ml: 1 }} 
                      />
                    )}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {/* Selected model description */}
            <Box sx={{ mt: 2 }}>
              {availableModels.find(model => model.id === selectedModelId)?.description}
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Prompt
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Define how the AI should behave when generating responses.
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={10}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              variant="outlined"
              placeholder="Enter system prompt"
              sx={{ mb: 3 }}
            />
            
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button 
                variant="contained" 
                color="primary" 
                startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                onClick={handleSaveSettings}
                disabled={isSaving}
              >
                Save Settings
              </Button>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Alert severity="info">
            The selected model and system prompt will be used for all future processing. 
            Current processing jobs will continue with their original settings.
          </Alert>
        </Grid>
      </Grid>
      
      <Snackbar
        open={showSuccess}
        autoHideDuration={5000}
        onClose={() => setShowSuccess(false)}
        message="Settings saved successfully"
      />
    </Box>
  );
};

export default Models; 