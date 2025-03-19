#!/usr/bin/env python3

"""
Test script for the modified llm_api.py
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.llm_api import query_llm, load_provider_models

def test_provider(provider: str, model: str = None):
    """Test a specific provider with various parameter combinations"""
    print(f"\nTesting {provider} provider" + (f" with model {model}" if model else ""))
    
    print("\n1. Testing with default parameters...")
    response = query_llm(
        "Hello, how are you?", 
        provider=provider,
        model=model
    )
    print(f"Response: {response}\n")
    
    print("2. Testing with custom temperature (0.5)...")
    response = query_llm(
        "Tell me a joke about programming", 
        provider=provider,
        model=model,
        temperature=0.5
    )
    print(f"Response: {response}\n")
    
    print("3. Testing with custom max_tokens (50)...")
    response = query_llm(
        "Explain quantum computing", 
        provider=provider,
        model=model,
        max_tokens=50
    )
    print(f"Response: {response}\n")
    
    print("4. Testing with both parameters...")
    response = query_llm(
        "Write a haiku about Python", 
        provider=provider,
        model=model,
        temperature=0.9,
        max_tokens=30
    )
    print(f"Response: {response}\n")

def test_provider_models():
    """Test all available models for each provider"""
    # Load provider configuration
    providers_config = load_provider_models()
    
    for provider, config in providers_config.items():
        print(f"\n{'='*50}")
        print(f"Testing provider: {config['name']} ({provider})")
        print(f"{'='*50}")
        
        # Test each model for the provider
        for model_info in config['models']:
            print(f"\n{'-'*40}")
            print(f"Testing model: {model_info['name']} ({model_info['id']})")
            print(f"Context length: {model_info['context_length']}")
            print(f"Description: {model_info['description']}")
            print(f"{'-'*40}\n")
            
            try:
                test_provider(provider, model_info['id'])
            except Exception as e:
                print(f"Error testing {model_info['id']}: {str(e)}")

def main():
    """Run tests for different providers"""
    # Test all models from provider_models.json
    test_provider_models()

if __name__ == "__main__":
    main() 