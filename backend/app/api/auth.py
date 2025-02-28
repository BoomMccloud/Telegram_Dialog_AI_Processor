from fastapi import APIRouter, HTTPException, status
from ..services.auth import create_auth_session, get_session_status, get_or_load_session, client_sessions, save_session_to_file, SESSIONS_DIR
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import json

router = APIRouter()

@router.post("/auth/qr")
async def create_qr_auth():
    """Create a new QR code authentication session using Telethon"""
    try:
        session = await create_auth_session()
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/session/{session_id}")
async def check_session_status(session_id: str):
    """Check the status of an authentication session"""
    status = await get_session_status(session_id)
    if not status:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return status

@router.post("/auth/session/{session_id}/refresh")
async def refresh_session(session_id: str) -> Dict:
    """
    Extend the expiration time of a session.
    Useful for development and testing to prevent sessions from expiring.
    
    Args:
        session_id: The ID of the session to refresh
        
    Returns:
        Updated session information
    """
    # Get the current session
    session = get_or_load_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Extend the session expiration
    session["expires_at"] = datetime.utcnow() + timedelta(hours=24)
    
    # Save to file
    save_session_to_file(session_id, session)
    
    # Return updated session info
    return {
        "status": "success",
        "session_id": session_id,
        "expires_at": session["expires_at"].isoformat(),
        "user_id": session.get("user_id"),
        "message": "Session expiration extended by 24 hours"
    }

@router.post("/auth/force-session/{session_id}")
async def force_create_session(session_id: str) -> Dict:
    """
    FOR DEVELOPMENT USE ONLY: Create a session file with the given ID.
    This is useful when developing to avoid having to scan QR codes repeatedly.
    
    WARNING: This should be disabled in production.
    
    Args:
        session_id: The session ID to create
        
    Returns:
        Created session information
    """
    # More permissive check for development mode - allow in any non-production environment
    if os.getenv("APP_ENV", "development").lower() in ["production", "prod"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    print(f"DEBUG: Force creating session {session_id}")
    print(f"DEBUG: APP_ENV={os.getenv('APP_ENV', 'development')}")
    
    # Create a mock session
    new_session = {
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
        "status": "authenticated",
        "user_id": 12345678,  # Mock user ID
        "client": None
    }
    
    # Ensure we're not overwriting an existing valid session
    existing_session = get_or_load_session(session_id)
    if existing_session and existing_session.get("status") == "authenticated":
        print(f"DEBUG: Session {session_id} already exists, overwriting it")
    
    # Save both in memory and to file
    client_sessions[session_id] = new_session
    
    # Explicitly save to file with detailed logging
    try:
        print(f"DEBUG: Attempting to save session {session_id} to file")
        save_session_to_file(session_id, new_session)
        print(f"DEBUG: Save to file completed")
        
        # Verify file was created
        file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if os.path.exists(file_path):
            print(f"DEBUG: Session file verification successful: {file_path}")
        else:
            print(f"ERROR: Session file not created despite no exceptions: {file_path}")
    except Exception as e:
        print(f"ERROR: Failed to save session {session_id} to file: {str(e)}")
    
    print(f"DEV MODE: Created forced session with ID: {session_id}")
    
    return {
        "status": "success",
        "message": f"Development session created with ID: {session_id}",
        "session_id": session_id,
        "expires_at": new_session["expires_at"].isoformat(),
        "debug_info": {
            "in_memory": session_id in client_sessions,
            "file_created": os.path.exists(os.path.join(SESSIONS_DIR, f"{session_id}.json")),
            "sessions_dir": SESSIONS_DIR,
            "app_env": os.getenv("APP_ENV", "development")
        }
    }

@router.get("/auth/sessions")
async def list_all_sessions() -> Dict:
    """
    FOR DEVELOPMENT USE ONLY: List all sessions in memory and on disk.
    This helps diagnose issues with session management.
    
    Returns:
        Dictionary containing information about all available sessions
    """
    # Only allow in non-production environments
    if os.getenv("APP_ENV", "development").lower() in ["production", "prod"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    # Get in-memory sessions
    memory_sessions = {}
    for session_id, session in client_sessions.items():
        memory_sessions[session_id] = {
            "status": session.get("status"),
            "user_id": session.get("user_id"),
            "created_at": session.get("created_at").isoformat() if isinstance(session.get("created_at"), datetime) else session.get("created_at"),
            "expires_at": session.get("expires_at").isoformat() if isinstance(session.get("expires_at"), datetime) else session.get("expires_at")
        }
    
    # Get file-based sessions
    file_sessions = {}
    if os.path.exists(SESSIONS_DIR):
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                session_id = filename[:-5]  # Remove .json extension
                try:
                    with open(os.path.join(SESSIONS_DIR, filename), 'r') as f:
                        session_data = json.load(f)
                        file_sessions[session_id] = {
                            "status": session_data.get("status"),
                            "user_id": session_data.get("user_id"),
                            "created_at": session_data.get("created_at"),
                            "expires_at": session_data.get("expires_at")
                        }
                except Exception as e:
                    file_sessions[session_id] = {"error": str(e)}
    
    return {
        "in_memory_sessions": memory_sessions,
        "file_sessions": file_sessions,
        "sessions_dir": SESSIONS_DIR,
        "environment": os.getenv("APP_ENV", "development"),
        "session_count": {
            "in_memory": len(memory_sessions),
            "file_based": len(file_sessions)
        },
        "debug_info": {
            "cwd": os.getcwd(),
            "sessions_dir_exists": os.path.exists(SESSIONS_DIR),
            "sessions_dir_is_dir": os.path.isdir(SESSIONS_DIR) if os.path.exists(SESSIONS_DIR) else False,
            "sessions_dir_writable": os.access(SESSIONS_DIR, os.W_OK) if os.path.exists(SESSIONS_DIR) else False,
            "app_env": os.getenv("APP_ENV", "development")
        }
    }

@router.get("/auth/debug-session/{session_id}")
async def debug_session(session_id: str) -> Dict:
    """
    FOR DEVELOPMENT USE ONLY: Debug detailed information about a specific session.
    
    Returns:
        Detailed information about the session from both memory and file storage
    """
    # Only allow in non-production environments
    if os.getenv("APP_ENV", "development").lower() in ["production", "prod"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    # Check in-memory session
    memory_session = client_sessions.get(session_id)
    memory_session_info = None
    if memory_session:
        memory_session_info = {
            "status": memory_session.get("status"),
            "user_id": memory_session.get("user_id"),
            "created_at": memory_session.get("created_at").isoformat() if isinstance(memory_session.get("created_at"), datetime) else memory_session.get("created_at"),
            "expires_at": memory_session.get("expires_at").isoformat() if isinstance(memory_session.get("expires_at"), datetime) else memory_session.get("expires_at"),
            "has_client": memory_session.get("client") is not None
        }
    
    # Check file session
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    file_session_info = None
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                file_data = json.load(f)
                file_session_info = {
                    "status": file_data.get("status"),
                    "user_id": file_data.get("user_id"),
                    "created_at": file_data.get("created_at"),
                    "expires_at": file_data.get("expires_at"),
                    "file_size": os.path.getsize(file_path),
                    "file_permissions": oct(os.stat(file_path).st_mode)[-3:],
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
        except Exception as e:
            file_session_info = {"error": str(e)}
    
    return {
        "session_id": session_id,
        "in_memory": memory_session_info is not None,
        "in_file": file_session_info is not None,
        "memory_session": memory_session_info,
        "file_session": file_session_info,
        "backend_session_lookup_path": file_path,
        "consistency_check": {
            "status_match": (memory_session_info is None or file_session_info is None) or 
                            (memory_session_info.get("status") == file_session_info.get("status")),
            "user_id_match": (memory_session_info is None or file_session_info is None) or 
                             (memory_session_info.get("user_id") == file_session_info.get("user_id"))
        }
    }

@router.get("/auth/session-ids")
async def list_session_ids():
    """
    FOR DEVELOPMENT USE ONLY: List all session IDs from all storage locations.
    This helps diagnose mismatches between different storage locations.
    
    Returns:
        Dictionary containing all session IDs from different sources
    """
    # Only allow in non-production environments
    if os.getenv("APP_ENV", "development").lower() in ["production", "prod"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    # Get in-memory session IDs
    memory_session_ids = list(client_sessions.keys())
    
    # Get file-based session IDs
    file_session_ids = []
    if os.path.exists(SESSIONS_DIR):
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                session_id = filename[:-5]  # Remove .json extension
                file_session_ids.append(session_id)
    
    # Check Telethon session files
    telethon_session_ids = []
    telethon_dir = os.path.join(os.path.dirname(SESSIONS_DIR), '')  # Parent of data dir
    if os.path.exists(telethon_dir):
        for filename in os.listdir(telethon_dir):
            if filename.endswith('.session'):
                session_id = filename[:-8]  # Remove .session extension
                telethon_session_ids.append(session_id)
    
    # Find inconsistencies
    only_in_memory = [sid for sid in memory_session_ids if sid not in file_session_ids]
    only_in_file = [sid for sid in file_session_ids if sid not in memory_session_ids]
    
    return {
        "memory_session_ids": memory_session_ids,
        "file_session_ids": file_session_ids,
        "telethon_session_ids": telethon_session_ids,
        "sessions_dir": SESSIONS_DIR,
        "telethon_dir": telethon_dir,
        "session_counts": {
            "memory": len(memory_session_ids),
            "file": len(file_session_ids),
            "telethon": len(telethon_session_ids)
        },
        "inconsistencies": {
            "only_in_memory": only_in_memory,
            "only_in_file": only_in_file
        }
    }

@router.post("/auth/cleanup-sessions")
async def cleanup_stale_sessions():
    """
    FOR DEVELOPMENT USE ONLY: Clean up stale QR login sessions.
    This helps resolve errors from incomplete QR login sessions.
    
    Returns:
        Details about the cleanup operation
    """
    # Only allow in non-production environments
    if os.getenv("APP_ENV", "development").lower() in ["production", "prod"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode"
        )
    
    now = datetime.utcnow()
    cleanup_results = {
        "expired_sessions_removed": 0,
        "pending_sessions_removed": 0,
        "error_sessions_removed": 0,
        "failed_cleanups": 0,
        "details": []
    }
    
    # 1. Clean up in-memory sessions first
    memory_sessions_to_remove = []
    for session_id, session in client_sessions.items():
        try:
            # Check for expired sessions
            if now > session.get("expires_at", now):
                memory_sessions_to_remove.append(session_id)
                cleanup_results["expired_sessions_removed"] += 1
                cleanup_results["details"].append(f"Expired session: {session_id}")
                continue
                
            # Check for pending sessions that are older than 10 minutes
            if session.get("status") == "pending" and session.get("created_at"):
                age = now - session["created_at"]
                if age.total_seconds() > 600:  # 10 minutes
                    memory_sessions_to_remove.append(session_id)
                    cleanup_results["pending_sessions_removed"] += 1
                    cleanup_results["details"].append(f"Stale pending session: {session_id}")
                    continue
                    
            # Check for error state sessions
            if session.get("status") == "error":
                memory_sessions_to_remove.append(session_id)
                cleanup_results["error_sessions_removed"] += 1
                cleanup_results["details"].append(f"Error state session: {session_id}")
                continue
        except Exception as e:
            cleanup_results["failed_cleanups"] += 1
            cleanup_results["details"].append(f"Failed to process memory session {session_id}: {str(e)}")
    
    # Disconnect and remove the flagged memory sessions
    for session_id in memory_sessions_to_remove:
        try:
            session = client_sessions.get(session_id)
            if session and session.get("client"):
                try:
                    await session["client"].disconnect()
                except Exception as e:
                    cleanup_results["details"].append(f"Error disconnecting client for {session_id}: {str(e)}")
            client_sessions.pop(session_id, None)
        except Exception as e:
            cleanup_results["failed_cleanups"] += 1
            cleanup_results["details"].append(f"Failed to remove memory session {session_id}: {str(e)}")
    
    # 2. Clean up file-based sessions
    if os.path.exists(SESSIONS_DIR):
        for filename in os.listdir(SESSIONS_DIR):
            if not filename.endswith('.json'):
                continue
                
            session_id = filename[:-5]  # Remove .json extension
            file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            
            try:
                # Skip if already cleaned up in memory
                if session_id in memory_sessions_to_remove:
                    continue
                    
                # Load session file
                try:
                    with open(file_path, 'r') as f:
                        session_data = json.load(f)
                except Exception as e:
                    # If we can't read the file, it's corrupted - remove it
                    cleanup_results["details"].append(f"Corrupted session file: {session_id}")
                    os.remove(file_path)
                    cleanup_results["error_sessions_removed"] += 1
                    continue
                
                # Check for expired sessions
                if "expires_at" in session_data:
                    try:
                        expires_at = datetime.fromisoformat(session_data["expires_at"]) if isinstance(session_data["expires_at"], str) else session_data["expires_at"]
                        if now > expires_at:
                            os.remove(file_path)
                            cleanup_results["expired_sessions_removed"] += 1
                            cleanup_results["details"].append(f"Expired session file: {session_id}")
                            continue
                    except Exception as e:
                        cleanup_results["details"].append(f"Error parsing expires_at for {session_id}: {str(e)}")
                
                # Check for pending sessions that are older than 10 minutes
                if session_data.get("status") == "pending" and "created_at" in session_data:
                    try:
                        created_at = datetime.fromisoformat(session_data["created_at"]) if isinstance(session_data["created_at"], str) else session_data["created_at"]
                        age = now - created_at
                        if age.total_seconds() > 600:  # 10 minutes
                            os.remove(file_path)
                            cleanup_results["pending_sessions_removed"] += 1
                            cleanup_results["details"].append(f"Stale pending session file: {session_id}")
                            continue
                    except Exception as e:
                        cleanup_results["details"].append(f"Error parsing created_at for {session_id}: {str(e)}")
                
                # Check for error state sessions
                if session_data.get("status") == "error":
                    os.remove(file_path)
                    cleanup_results["error_sessions_removed"] += 1
                    cleanup_results["details"].append(f"Error state session file: {session_id}")
                    continue
                
            except Exception as e:
                cleanup_results["failed_cleanups"] += 1
                cleanup_results["details"].append(f"Failed to process file session {session_id}: {str(e)}")
    
    # 3. Clean up orphaned Telethon session files
    # Only if they don't have corresponding JSON session files
    telethon_dir = os.path.join(os.path.dirname(SESSIONS_DIR), '')
    if os.path.exists(telethon_dir):
        # Get all valid session IDs (from memory and files)
        valid_session_ids = set(client_sessions.keys())
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.json'):
                valid_session_ids.add(filename[:-5])
        
        # Check for orphaned Telethon session files
        orphaned_count = 0
        for filename in os.listdir(telethon_dir):
            if filename.endswith('.session'):
                session_id = filename[:-8]  # Remove .session extension
                if session_id not in valid_session_ids:
                    try:
                        os.remove(os.path.join(telethon_dir, filename))
                        orphaned_count += 1
                        cleanup_results["details"].append(f"Removed orphaned Telethon session: {session_id}")
                    except Exception as e:
                        cleanup_results["failed_cleanups"] += 1
                        cleanup_results["details"].append(f"Failed to remove Telethon session {session_id}: {str(e)}")
        
        cleanup_results["orphaned_telethon_removed"] = orphaned_count
    
    # Return overall results
    total_removed = (
        cleanup_results["expired_sessions_removed"] + 
        cleanup_results["pending_sessions_removed"] + 
        cleanup_results["error_sessions_removed"] + 
        cleanup_results.get("orphaned_telethon_removed", 0)
    )
    
    return {
        "status": "success",
        "total_sessions_removed": total_removed,
        "cleanup_details": cleanup_results,
        "message": f"Session cleanup complete. Removed {total_removed} stale or expired sessions."
    } 