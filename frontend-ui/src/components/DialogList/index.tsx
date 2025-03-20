import React from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  ListItemButton,
  Avatar,
  Badge,
  CircularProgress,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SendIcon from '@mui/icons-material/Send';
import { BaseDialog, Response } from '../../types';

interface DialogListProps {
  loading: boolean;
  items: BaseDialog[] | Response[];
  selectedItemId: string | number | null;
  searchQuery: string;
  isPending: boolean;
  onSelectItem: (item: BaseDialog | Response) => void;
}

const DialogList: React.FC<DialogListProps> = ({
  loading,
  items,
  selectedItemId,
  searchQuery,
  isPending,
  onSelectItem,
}) => {
  // Filter responses or dialogs based on search query
  const filteredItems = isPending 
    ? (items as BaseDialog[]).filter(dialog => 
        dialog.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : (items as Response[]).filter(response => 
        response.dialog_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        response.suggested_response.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (response.edited_response && response.edited_response.toLowerCase().includes(searchQuery.toLowerCase()))
      );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (filteredItems.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', my: 4 }}>
        <Typography variant="body2" color="text.secondary">
          {isPending 
            ? "No unread dialogs" 
            : "No responses found"
          }
        </Typography>
      </Box>
    );
  }

  return (
    <List sx={{ 
      bgcolor: 'background.paper', 
      borderRadius: 1,
      height: '100%',
      overflow: 'auto',
      maxHeight: '500px'
    }}>
      {filteredItems.map((item) => {
        // Determine if this is a dialog or response
        const isDialog = 'type' in item;
        
        // For dialogs
        if (isDialog) {
          const dialog = item as BaseDialog;
          return (
            <ListItem 
              key={dialog.id} 
              disablePadding
              divider
            >
              <ListItemButton
                selected={selectedItemId === dialog.id}
                onClick={() => onSelectItem(dialog)}
                sx={{
                  borderLeft: selectedItemId === dialog.id ? 3 : 0,
                  borderColor: 'primary.main',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
              >
                <ListItemAvatar>
                  <Badge 
                    overlap="circular"
                    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                    badgeContent={dialog.unread_count}
                    color="error"
                  >
                    <Avatar>{dialog.name.charAt(0).toUpperCase()}</Avatar>
                  </Badge>
                </ListItemAvatar>
                <ListItemText 
                  primary={dialog.name} 
                  secondary={
                    <Typography
                      sx={{ display: 'inline', color: 'text.secondary' }}
                      component="span"
                      variant="body2"
                      noWrap
                    >
                      {dialog.type} · {dialog.unread_count} unread
                    </Typography>
                  }
                />
              </ListItemButton>
            </ListItem>
          );
        }
        
        // For responses
        const response = item as Response;
        return (
          <ListItem 
            key={response.id} 
            disablePadding
            divider
          >
            <ListItemButton
              selected={selectedItemId === response.id}
              onClick={() => onSelectItem(response)}
              sx={{
                borderLeft: selectedItemId === response.id ? 3 : 0,
                borderColor: 'primary.main',
                '&:hover': { bgcolor: 'action.hover' }
              }}
            >
              <ListItemAvatar>
                <Badge 
                  overlap="circular"
                  anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                  badgeContent={
                    response.status === 'approved' ? 
                      <CheckCircleIcon color="info" fontSize="small" /> :
                      response.status === 'sent' ?
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
                  </Typography>
                }
              />
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
  );
};

export default DialogList; 