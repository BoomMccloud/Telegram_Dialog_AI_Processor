#!/usr/bin/env python3
import argparse
import requests
import json
import sys

def verify_session(token, host="http://localhost:8000"):
    """Verify a session using the provided JWT token"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{host}/api/auth/session/verify"
    print(f"Verifying session at: {url}")
    print(f"Using token: {token[:10]}...\n")
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        print(f"Status code: {response.status_code}")
        print(f"Session status: {data.get('status')}")
        print(f"Telegram ID: {data.get('telegram_id')}")
        
        if data.get("user"):
            print(f"User: {data['user'].get('username')} ({data['user'].get('first_name')} {data['user'].get('last_name')})")
        
        print(f"Expires at: {data.get('expires_at')}")
        print(f"\nComplete response:")
        print(json.dumps(data, indent=2))
        
        return data
    except requests.RequestException as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response")
        print(f"Response text: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify a Telegram session token")
    parser.add_argument("token", help="JWT token to verify (without Bearer prefix)")
    parser.add_argument("--host", default="http://localhost:8000", help="Host URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    verify_session(args.token, args.host)
