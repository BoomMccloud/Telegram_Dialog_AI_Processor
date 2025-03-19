import React from 'react';
import {
  FormControl,
  Select,
  MenuItem,
  SelectChangeEvent,
  Typography,
  Box,
} from '@mui/material';
import { Provider } from '../../api/models';

interface ProviderSelectProps {
  providers: Record<string, Provider>;
  activeProvider: string;
  onProviderChange: (provider: string) => void;
}

export const ProviderSelect: React.FC<ProviderSelectProps> = ({
  providers,
  activeProvider,
  onProviderChange,
}) => {
  const handleChange = (event: SelectChangeEvent) => {
    onProviderChange(event.target.value);
  };

  return (
    <FormControl fullWidth>
      <Select
        id="provider-select"
        value={activeProvider}
        onChange={handleChange}
      >
        {Object.entries(providers).map(([id, provider]) => (
          <MenuItem key={id} value={id}>
            <Box>
              <Typography variant="body1">{provider.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {provider.description}
              </Typography>
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}; 