import React from 'react';
import {
  Box,
  Typography,
  Slider,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
} from '@mui/material';
import { ModelParameter, ProviderSettings } from '../../api/models';

interface ParameterControlsProps {
  parameters: ModelParameter[];
  values: ProviderSettings;
  onChange: (parameterId: string, value: number | string) => void;
}

export const ParameterControls: React.FC<ParameterControlsProps> = ({
  parameters,
  values,
  onChange,
}) => {
  const handleSliderChange = (parameterId: string) => (_: Event, value: number | number[]) => {
    onChange(parameterId, value as number);
  };

  const handleTextChange = (parameterId: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    const parameter = parameters.find(p => p.id === parameterId);
    if (!parameter) return;

    if (parameter.min !== undefined && parameter.max !== undefined) {
      const numValue = Number(value);
      if (!isNaN(numValue) && numValue >= parameter.min && numValue <= parameter.max) {
        onChange(parameterId, numValue);
      }
    } else {
      onChange(parameterId, value);
    }
  };

  const handleSelectChange = (parameterId: string) => (event: SelectChangeEvent<string>) => {
    onChange(parameterId, event.target.value);
  };

  const getParameterValue = (parameter: ModelParameter): number | string => {
    const value = values[parameter.id];
    if (value === undefined) return parameter.default;
    return typeof parameter.default === 'number' ? Number(value) : String(value);
  };

  return (
    <Box>
      {parameters.map((parameter) => (
        <Box key={parameter.id} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            {parameter.name}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
            {parameter.description}
          </Typography>

          {parameter.options ? (
            // Dropdown for options
            <FormControl fullWidth size="small">
              <InputLabel id={`${parameter.id}-label`}>{parameter.name}</InputLabel>
              <Select
                labelId={`${parameter.id}-label`}
                value={String(getParameterValue(parameter))}
                label={parameter.name}
                onChange={handleSelectChange(parameter.id)}
              >
                {parameter.options.map((option) => (
                  <MenuItem key={option} value={option}>
                    {option}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : parameter.min !== undefined && parameter.max !== undefined && parameter.step ? (
            // Slider for numeric values with min/max
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Slider
                value={Number(getParameterValue(parameter))}
                onChange={handleSliderChange(parameter.id)}
                min={parameter.min}
                max={parameter.max}
                step={parameter.step}
                valueLabelDisplay="auto"
                sx={{ flexGrow: 1 }}
              />
              <TextField
                size="small"
                value={getParameterValue(parameter)}
                onChange={handleTextChange(parameter.id)}
                type="number"
                inputProps={{
                  min: parameter.min,
                  max: parameter.max,
                  step: parameter.step,
                }}
                sx={{ width: 120 }}
              />
            </Box>
          ) : (
            // Text input for other cases
            <TextField
              fullWidth
              size="small"
              value={getParameterValue(parameter)}
              onChange={handleTextChange(parameter.id)}
            />
          )}
        </Box>
      ))}
    </Box>
  );
}; 