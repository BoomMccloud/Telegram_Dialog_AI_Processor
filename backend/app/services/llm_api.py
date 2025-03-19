#!/usr/bin/env /workspace/tmp_windsurf/venv/bin/python3

import google.generativeai as genai
from openai import OpenAI, AzureOpenAI
from anthropic import Anthropic
import argparse
import os
from dotenv import load_dotenv
from pathlib import Path
import sys
import base64
from typing import Optional, Union, List, Dict, Any
import mimetypes
import time
import json
from . import token_tracker
from .token_tracker import TokenUsage, APIResponse, get_token_tracker

# Add config path
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
PROVIDER_MODELS_PATH = CONFIG_DIR / "provider_models.json"

def load_environment():
    """Load environment variables from .env files in order of precedence"""
    # Order of precedence:
    # 1. System environment variables (already loaded)
    # 2. .env.local (user-specific overrides)
    # 3. .env (project defaults)
    # 4. .env.example (example configuration)
    
    env_files = ['.env.local', '.env', '.env.example']
    env_loaded = False
    
    print("Current working directory:", Path('.').absolute(), file=sys.stderr)
    print("Looking for environment files:", env_files, file=sys.stderr)
    
    for env_file in env_files:
        env_path = Path('.') / env_file
        print(f"Checking {env_path.absolute()}", file=sys.stderr)
        if env_path.exists():
            print(f"Found {env_file}, loading variables...", file=sys.stderr)
            load_dotenv(dotenv_path=env_path)
            env_loaded = True
            print(f"Loaded environment variables from {env_file}", file=sys.stderr)
            # Print loaded keys (but not values for security)
            with open(env_path) as f:
                keys = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
                print(f"Keys loaded from {env_file}: {keys}", file=sys.stderr)
    
    if not env_loaded:
        print("Warning: No .env files found. Using system environment variables only.", file=sys.stderr)
        print("Available system environment variables:", list(os.environ.keys()), file=sys.stderr)

# Load environment variables at module import
load_environment()

def encode_image_file(image_path: str) -> tuple[str, str]:
    """
    Encode an image file to base64 and determine its MIME type.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        tuple: (base64_encoded_string, mime_type)
    """
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = 'image/png'  # Default to PNG if type cannot be determined
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    return encoded_string, mime_type

def create_llm_client(provider="openai"):
    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key
        )
    elif provider == "azure":
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables")
        return AzureOpenAI(
            api_key=api_key,
            api_version="2024-08-01-preview",
            azure_endpoint="https://msopenai.openai.azure.com"
        )
    elif provider == "deepseek":
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )
    elif provider == "anthropic":
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return Anthropic(
            api_key=api_key
        )
    elif provider == "gemini":
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        return genai
    elif provider == "local":
        return OpenAI(
            base_url="http://192.168.180.137:8006/v1",
            api_key="not-needed"
        )
    elif provider == "ollama":
        # Ollama uses OpenAI-compatible API
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        return OpenAI(
            base_url=f"{ollama_host}/v1",
            api_key="not-needed"  # Ollama doesn't require an API key
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def load_provider_models() -> Dict[str, Any]:
    """Load and parse provider_models.json"""
    try:
        with open(PROVIDER_MODELS_PATH, 'r') as f:
            config = json.load(f)
            return config.get("providers", {})
    except Exception as e:
        print(f"Error loading provider_models.json: {e}", file=sys.stderr)
        return {}

def get_default_model(provider: str, providers_config: Dict[str, Any]) -> str:
    """Get the default model for a provider from config"""
    provider_config = providers_config.get(provider, {})
    return provider_config.get("default_model") or provider_config.get("models", [{}])[0].get("id")

def get_valid_models(provider: str, providers_config: Dict[str, Any]) -> List[str]:
    """Get list of valid models for a provider from config"""
    provider_config = providers_config.get(provider, {})
    return [model["id"] for model in provider_config.get("models", [])]

def query_llm(prompt: str, client=None, model=None, provider="openai", image_path: Optional[str] = None, temperature=None, max_tokens=None) -> Optional[str]:
    """
    Query an LLM with a prompt and optional image attachment.
    
    Args:
        prompt (str): The text prompt to send
        client: The LLM client instance
        model (str, optional): The model to use
        provider (str): The API provider to use
        image_path (str, optional): Path to an image file to attach
        temperature (float, optional): Controls randomness in the model's output (0.0-1.0)
        max_tokens (int, optional): Maximum number of tokens to generate
        
    Returns:
        Optional[str]: The LLM's response or None if there was an error
    """
    if client is None:
        client = create_llm_client(provider)
    
    try:
        # Load provider configuration
        providers_config = load_provider_models()
        
        # Set default model from config
        if model is None:
            model = get_default_model(provider, providers_config)
        else:
            # Validate model if provided
            valid_models = get_valid_models(provider, providers_config)
            if valid_models and model not in valid_models:
                print(f"Warning: Model {model} not found in config for provider {provider}. Using default.", file=sys.stderr)
                model = get_default_model(provider, providers_config)
        
        # Get provider parameters from config
        provider_config = providers_config.get(provider, {})
        provider_params = {
            param["id"]: param
            for param in provider_config.get("parameters", [])
        }
        
        # Set default temperature and max_tokens from config if not provided
        if temperature is None and "temperature" in provider_params:
            temperature = provider_params["temperature"].get("default", 0.7)
        
        if max_tokens is None and "max_tokens" in provider_params:
            max_tokens = provider_params["max_tokens"].get("default", 1000)
        
        start_time = time.time()
        
        if provider in ["openai", "local", "deepseek", "azure", "ollama"]:
            messages = [{"role": "user", "content": []}]
            
            # Add text content
            messages[0]["content"].append({
                "type": "text",
                "text": prompt
            })
            
            # Add image content if provided
            if image_path:
                if provider == "openai":
                    encoded_image, mime_type = encode_image_file(image_path)
                    messages[0]["content"] = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"}}
                    ]
            
            kwargs = {
                "model": model,
                "messages": messages,
            }
            
            # Add optional parameters if provided
            if temperature is not None:
                kwargs["temperature"] = temperature
            else:
                kwargs["temperature"] = 0.7  # Default
                
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            
            # Add o1-specific parameters
            if model == "o1":
                kwargs["response_format"] = {"type": "text"}
                kwargs["reasoning_effort"] = "low"
                if "temperature" in kwargs:
                    del kwargs["temperature"]
            
            response = client.chat.completions.create(**kwargs)
            thinking_time = time.time() - start_time
            
            # Track token usage
            token_usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                reasoning_tokens=response.usage.reasoning_tokens if model == "o1" else None  # Only o1 model provides reasoning tokens
            )
            
            # Skip cost calculation for now
            api_response = APIResponse(
                content=response.choices[0].message.content,
                token_usage=token_usage,
                cost=0.0,  # Set cost to 0 for now
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            get_token_tracker().track_request(api_response)
            
            return response.choices[0].message.content
            
        elif provider == "anthropic":
            messages = [{"role": "user", "content": []}]
            
            # Add text content
            messages[0]["content"].append({
                "type": "text",
                "text": prompt
            })
            
            # Add image content if provided
            if image_path:
                encoded_image, mime_type = encode_image_file(image_path)
                messages[0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": encoded_image
                    }
                })
                
            # Build request parameters
            kwargs = {
                "model": model,
                "messages": messages
            }
            
            # Add optional parameters if provided
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = 1000  # Default
                
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            response = client.messages.create(**kwargs)
            thinking_time = time.time() - start_time
            
            # Track token usage
            token_usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
            )
            
            # Skip cost calculation for now
            api_response = APIResponse(
                content=response.content[0].text,
                token_usage=token_usage,
                cost=0.0,  # Set cost to 0 for now
                thinking_time=thinking_time,
                provider=provider,
                model=model
            )
            get_token_tracker().track_request(api_response)
            
            return response.content[0].text
            
        elif provider == "gemini":
            model_obj = client.GenerativeModel(model)
            
            # Build generation config
            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
                
            # Apply generation config if parameters were provided
            if generation_config:
                response = model_obj.generate_content(
                    prompt, 
                    generation_config=client.GenerationConfig(**generation_config)
                )
            else:
                response = model_obj.generate_content(prompt)
                
            return response.text
            
    except Exception as e:
        print(f"Error querying LLM: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Query an LLM with a prompt')
    parser.add_argument('--prompt', type=str, help='The prompt to send to the LLM', required=True)
    parser.add_argument('--provider', choices=['openai','anthropic','gemini','local','deepseek','azure','ollama'], default='openai', help='The API provider to use')
    parser.add_argument('--model', type=str, help='The model to use (default depends on provider)')
    parser.add_argument('--image', type=str, help='Path to an image file to attach to the prompt')
    parser.add_argument('--temperature', type=float, help='Controls randomness in output (0.0-1.0)')
    parser.add_argument('--max-tokens', type=int, help='Maximum number of tokens to generate')
    args = parser.parse_args()

    if not args.model:
        if args.provider == 'openai':
            args.model = "gpt-4o" 
        elif args.provider == "deepseek":
            args.model = "deepseek-chat"
        elif args.provider == 'anthropic':
            args.model = "claude-3-5-sonnet-20241022"
        elif args.provider == 'gemini':
            args.model = "gemini-2.0-flash-exp"
        elif args.provider == 'azure':
            args.model = os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt-4o-ms')  # Get from env with fallback
        elif args.provider == 'ollama':
            args.model = os.getenv('OLLAMA_MODEL', 'llama2')  # Default to llama2 if not specified

    client = create_llm_client(args.provider)
    response = query_llm(
        args.prompt, 
        client, 
        model=args.model, 
        provider=args.provider, 
        image_path=args.image,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    if response:
        print(response)
    else:
        print("Failed to get response from LLM")

if __name__ == "__main__":
    main()