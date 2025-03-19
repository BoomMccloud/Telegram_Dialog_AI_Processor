import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Alert,
  Snackbar,
  CircularProgress,
  Button,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import { ProviderSelect } from '../../components/ModelConfig/ProviderSelect';
import { ModelSelect } from '../../components/ModelConfig/ModelSelect';
import { ParameterControls } from '../../components/ModelConfig/ParameterControls';
import { api } from '../../services/api';
import type { ProviderModels, ModelSettings } from '../../services/api';

const ModelsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<ProviderModels | null>(null);
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const [providersData, settingsData] = await Promise.all([
          api.config.getProviderModels(),
          api.config.getModelSettings()
        ]);
        
        setProviders(providersData);
        setSettings(settingsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load model configuration');
        console.error('Error loading model configuration:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Handlers
  const handleProviderChange = (providerId: string) => {
    if (!settings || !providers) return;

    const provider = providers.providers[providerId];
    if (!provider) return;

    setSettings({
      ...settings,
      active_provider: providerId,
      providers: {
        ...settings.providers,
        [providerId]: {
          model: provider.default_model,
          temperature: provider.parameters.find(p => p.id === 'temperature')?.default as number || 0.7,
          max_tokens: provider.parameters.find(p => p.id === 'max_tokens')?.default as number || 1000,
        },
      },
    });
    setHasUnsavedChanges(true);
  };

  const handleModelChange = (modelId: string) => {
    if (!settings || !providers) return;

    const activeProvider = settings.active_provider;
    setSettings({
      ...settings,
      providers: {
        ...settings.providers,
        [activeProvider]: {
          ...settings.providers[activeProvider],
          model: modelId,
        },
      },
    });
    setHasUnsavedChanges(true);
  };

  const handleParameterChange = (parameterId: string, value: number | string) => {
    if (!settings) return;

    const activeProvider = settings.active_provider;
    setSettings({
      ...settings,
      providers: {
        ...settings.providers,
        [activeProvider]: {
          ...settings.providers[activeProvider],
          [parameterId]: value,
        },
      },
    });
    setHasUnsavedChanges(true);
  };

  const handleSave = async () => {
    if (!settings) return;

    setIsSaving(true);
    try {
      const newSettings = await api.config.updateModelSettings({
        active_provider: settings.active_provider,
        providers: settings.providers,
      });
      setSettings(newSettings);
      setHasUnsavedChanges(false);
      setSuccess('Settings saved successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <Box>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!providers || !settings) {
    return (
      <Box>
        <Alert severity="error">Failed to load model configuration. Please refresh the page to try again.</Alert>
      </Box>
    );
  }

  const activeProvider = providers.providers[settings.active_provider];
  const activeProviderSettings = settings.providers[settings.active_provider];

  if (!activeProvider || !activeProviderSettings) {
    return (
      <Box>
        <Alert severity="error">Invalid provider configuration. Please contact support.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Model Configuration
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              AI Provider
            </Typography>
            <ProviderSelect
              providers={providers.providers}
              activeProvider={settings.active_provider}
              onProviderChange={handleProviderChange}
            />
            
            <Box sx={{ mt: 4 }}>
              <Typography variant="h6" gutterBottom>
                Model
              </Typography>
              <ModelSelect
                models={activeProvider.models}
                selectedModel={activeProviderSettings.model}
                onModelChange={handleModelChange}
              />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Parameters
            </Typography>
            <ParameterControls
              parameters={[
                ...activeProvider.parameters,
                ...(activeProvider.special_parameters || []),
              ]}
              values={activeProviderSettings}
              onChange={handleParameterChange}
            />
            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSave}
                disabled={isSaving || !hasUnsavedChanges}
                startIcon={isSaving ? <CircularProgress size={20} /> : <SaveIcon />}
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ModelsPage; 