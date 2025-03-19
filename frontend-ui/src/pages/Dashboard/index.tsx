import React from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Paper, 
  Card, 
  CardContent, 
  CardActions,
  Button,
  Divider,
  Chip,
} from '@mui/material';
import { 
  Check as CheckIcon, 
  Close as CloseIcon,
  Warning as WarningIcon,
  Message as MessageIcon,
} from '@mui/icons-material';

const Dashboard = () => {
  // Sample data - in a real app, this would come from API
  const pendingResponses = 5;
  const processedDialogs = 3;
  const activeModel = 'GPT-4';
  
  // Urgent actions that need response
  const urgentActions = [
    { 
      id: 1, 
      type: 'message', 
      title: 'Response to John', 
      description: 'AI generated response for conversation about project timeline',
      timestamp: '10 minutes ago',
    },
    { 
      id: 2, 
      type: 'message', 
      title: 'Response to Marketing Group', 
      description: 'AI generated response for discussion about Q2 metrics',
      timestamp: '15 minutes ago',
    },
    { 
      id: 3, 
      type: 'system', 
      title: 'Authentication needed', 
      description: 'Telegram authentication has expired, needs renewal',
      timestamp: '30 minutes ago',
    },
  ];

  // Function to get the appropriate icon for the action type
  const getActionIcon = (type: string) => {
    switch (type) {
      case 'message':
        return <MessageIcon color="primary" />;
      case 'system':
        return <WarningIcon color="warning" />;
      default:
        return <MessageIcon />;
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Dashboard
      </Typography>
      
      {/* Status Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography color="text.secondary" variant="subtitle2" sx={{ mb: 1 }}>
              Pending Responses
            </Typography>
            <Typography variant="h3" component="div" sx={{ fontWeight: 'medium', mb: 1 }}>
              {pendingResponses}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Messages awaiting your review
            </Typography>
            <Button 
              variant="text" 
              color="primary" 
              size="small" 
              sx={{ mt: 'auto', alignSelf: 'flex-start' }}
              href="/messages"
            >
              View messages
            </Button>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography color="text.secondary" variant="subtitle2" sx={{ mb: 1 }}>
              Active Dialogs
            </Typography>
            <Typography variant="h3" component="div" sx={{ fontWeight: 'medium', mb: 1 }}>
              {processedDialogs}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Telegram conversations being processed
            </Typography>
            <Button 
              variant="text" 
              color="primary" 
              size="small" 
              sx={{ mt: 'auto', alignSelf: 'flex-start' }}
              href="/data"
            >
              Manage dialogs
            </Button>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper elevation={2} sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography color="text.secondary" variant="subtitle2" sx={{ mb: 1 }}>
              AI Model
            </Typography>
            <Typography variant="h5" component="div" sx={{ fontWeight: 'medium', mb: 1 }}>
              {activeModel}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Currently active model for processing
            </Typography>
            <Button 
              variant="text" 
              color="primary" 
              size="small" 
              sx={{ mt: 'auto', alignSelf: 'flex-start' }}
              href="/models"
            >
              Change model
            </Button>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Urgent Actions Section */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Urgent Actions
      </Typography>
      
      <Grid container spacing={2}>
        {urgentActions.map((action) => (
          <Grid item xs={12} key={action.id}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {getActionIcon(action.type)}
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    {action.title}
                  </Typography>
                  <Chip 
                    label={action.timestamp} 
                    size="small" 
                    variant="outlined"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {action.description}
                </Typography>
              </CardContent>
              <Divider />
              <CardActions>
                <Button 
                  size="small" 
                  variant="contained" 
                  color="primary"
                  startIcon={<CheckIcon />}
                >
                  Approve
                </Button>
                {action.type === 'message' && (
                  <Button 
                    size="small" 
                    variant="outlined"
                    href={`/messages/${action.id}`}
                  >
                    Edit
                  </Button>
                )}
                <Button 
                  size="small" 
                  variant="contained" 
                  color="error"
                  startIcon={<CloseIcon />}
                  sx={{ ml: 'auto' }}
                >
                  Reject
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default Dashboard; 