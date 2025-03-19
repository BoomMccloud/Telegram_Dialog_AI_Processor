import React from 'react';
import {
  FormControl,
  Select,
  MenuItem,
  SelectChangeEvent,
  Typography,
  Box,
  Chip,
} from '@mui/material';
import { Model } from '../../api/models';

interface ModelSelectProps {
  models: Model[];
  selectedModel: string;
  onModelChange: (model: string) => void;
}

export const ModelSelect: React.FC<ModelSelectProps> = ({
  models,
  selectedModel,
  onModelChange,
}) => {
  const handleChange = (event: SelectChangeEvent) => {
    onModelChange(event.target.value);
  };

  return (
    <Box>
      <FormControl fullWidth>
        <Select
          id="model-select"
          value={selectedModel}
          onChange={handleChange}
        >
          {models.map((model) => (
            <MenuItem key={model.id} value={model.id}>
              <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body1">{model.name}</Typography>
                  <Chip 
                    label={`${Math.round(model.context_length / 1000)}k ctx`} 
                    size="small" 
                    color="primary" 
                    variant="outlined"
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {model.description}
                </Typography>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}; 