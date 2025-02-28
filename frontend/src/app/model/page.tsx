'use client';

import { useState, useEffect } from 'react';
import AppLayout from '../AppLayout';
import { useSession } from '../SessionContext';

interface ModelOption {
  id: string;
  name: string;
  description: string;
  logoUrl: string;
}

export default function ModelPage() {
  const [selectedModel, setSelectedModel] = useState<string>('ollama');
  const [saving, setSaving] = useState<boolean>(false);
  const [saved, setSaved] = useState<boolean>(false);
  const { managedFetch } = useSession();

  // List of available models
  const models: ModelOption[] = [
    {
      id: 'chatgpt',
      name: 'ChatGPT',
      description: 'OpenAI\'s GPT models with strong general knowledge and reasoning.',
      logoUrl: '/images/openai-logo.svg'
    },
    {
      id: 'claude',
      name: 'Claude',
      description: 'Anthropic\'s Claude models with great instruction following capabilities.',
      logoUrl: '/images/claude-logo.svg'
    },
    {
      id: 'deepseek',
      name: 'DeepSeek',
      description: 'Advanced reasoning model with strong capabilities in code understanding.',
      logoUrl: '/images/deepseek-logo.svg'
    },
    {
      id: 'ollama',
      name: 'Ollama',
      description: 'Run Llama and other large language models locally.',
      logoUrl: '/images/ollama-logo.svg'
    }
  ];

  // Load saved model preference on page load
  useEffect(() => {
    const fetchSavedModel = async () => {
      try {
        // For now, fallback to localStorage
        // This would be replaced with an API call to get user preferences
        const savedModel = localStorage.getItem('selectedModel');
        if (savedModel) {
          setSelectedModel(savedModel);
        }
      } catch (error) {
        console.error('Error loading model preference:', error);
      }
    };

    fetchSavedModel();
  }, [managedFetch]);

  // Handle model selection
  const handleModelSelect = (modelId: string) => {
    setSelectedModel(modelId);
  };

  // Save model selection
  const saveModelSelection = async () => {
    setSaving(true);
    
    try {
      // This would be replaced with actual API call to backend
      // For now, just store in localStorage
      localStorage.setItem('selectedModel', selectedModel);
      
      // Show saved confirmation
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Error saving model selection:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppLayout>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="md:flex md:items-center md:justify-between">
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Model Selection
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Choose which AI model to use for processing your Telegram messages
              </p>
            </div>
            <div className="mt-4 flex md:mt-0 md:ml-4">
              <button
                type="button"
                onClick={saveModelSelection}
                disabled={saving}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Selection'}
              </button>
            </div>
          </div>

          {saved && (
            <div className="mt-4 bg-green-50 dark:bg-green-900 p-4 rounded-md">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    Model selection saved successfully!
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
            {models.map((model) => (
              <div 
                key={model.id}
                onClick={() => handleModelSelect(model.id)}
                className={`relative rounded-lg border p-6 cursor-pointer ${
                  selectedModel === model.id
                    ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
              >
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0 h-12 w-12 flex items-center justify-center rounded-lg bg-white dark:bg-gray-800 p-2">
                    {/* Placeholder for logo - would be replaced with actual images */}
                    <div className="text-2xl font-bold text-gray-700 dark:text-gray-300">
                      {model.name.charAt(0)}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-xl font-medium text-gray-900 dark:text-white">
                      {model.name}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      {model.description}
                    </p>
                  </div>
                </div>
                
                {selectedModel === model.id && (
                  <div className="absolute top-4 right-4">
                    <span className="h-6 w-6 flex items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                      <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-8">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Model Configuration</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Additional settings for the selected model will appear here
            </p>
            
            <div className="mt-4 bg-white dark:bg-gray-800 shadow rounded-lg p-6">
              {selectedModel === 'ollama' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="ollama-endpoint" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Ollama Endpoint
                    </label>
                    <input
                      type="text"
                      name="ollama-endpoint"
                      id="ollama-endpoint"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="http://localhost:11434"
                      defaultValue="http://localhost:11434"
                    />
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      The URL where your Ollama instance is running
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="ollama-model" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Model Name
                    </label>
                    <select
                      id="ollama-model"
                      name="ollama-model"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      defaultValue="llama3"
                    >
                      <option value="llama3">Llama 3 (8B)</option>
                      <option value="llama3:70b">Llama 3 (70B)</option>
                      <option value="mistral">Mistral</option>
                      <option value="codellama">CodeLlama</option>
                    </select>
                  </div>
                </div>
              )}
              
              {selectedModel === 'chatgpt' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="openai-api-key" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      OpenAI API Key
                    </label>
                    <input
                      type="password"
                      name="openai-api-key"
                      id="openai-api-key"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="sk-..."
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="openai-model" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Model
                    </label>
                    <select
                      id="openai-model"
                      name="openai-model"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      defaultValue="gpt-4o"
                    >
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4-turbo">GPT-4 Turbo</option>
                      <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    </select>
                  </div>
                </div>
              )}
              
              {selectedModel === 'claude' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="claude-api-key" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Anthropic API Key
                    </label>
                    <input
                      type="password"
                      name="claude-api-key"
                      id="claude-api-key"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="sk-ant-..."
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="claude-model" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Model
                    </label>
                    <select
                      id="claude-model"
                      name="claude-model"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      defaultValue="claude-3-5-sonnet"
                    >
                      <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                      <option value="claude-3-opus">Claude 3 Opus</option>
                      <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                      <option value="claude-3-haiku">Claude 3 Haiku</option>
                    </select>
                  </div>
                </div>
              )}
              
              {selectedModel === 'deepseek' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="deepseek-api-key" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      DeepSeek API Key
                    </label>
                    <input
                      type="password"
                      name="deepseek-api-key"
                      id="deepseek-api-key"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="..."
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="deepseek-model" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Model
                    </label>
                    <select
                      id="deepseek-model"
                      name="deepseek-model"
                      className="mt-1 block w-full border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      defaultValue="deepseek-chat"
                    >
                      <option value="deepseek-chat">DeepSeek Chat</option>
                      <option value="deepseek-coder">DeepSeek Coder</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
} 