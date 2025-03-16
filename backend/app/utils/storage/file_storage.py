"""
File-based storage utility for temporary message storage
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import logging
import asyncio

from app.db.models.message import Message
from app.utils.storage.metadata import ProcessingRunMetadata, ProcessingStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)

class MessageFileStorage:
    """Utility for managing temporary message files"""
    
    def __init__(self, base_dir: str = "/tmp/telegram_processor"):
        """
        Initialize the file storage utility
        
        Args:
            base_dir: Base directory for storing message files
        """
        self.base_dir = Path(base_dir)
        self._ensure_base_dir()
    
    def _ensure_base_dir(self) -> None:
        """Ensure the base directory exists"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_user_dir(self, user_id: str) -> Path:
        """Get the directory for a user"""
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def get_dialog_dir(self, user_id: str, dialog_id: str) -> Path:
        """Get the directory for a dialog"""
        dialog_dir = self.get_user_dir(user_id) / str(dialog_id)
        dialog_dir.mkdir(exist_ok=True)
        return dialog_dir
    
    def create_processing_run(self, user_id: str, dialog_id: str) -> ProcessingRunMetadata:
        """
        Create a new processing run
        
        Args:
            user_id: User ID
            dialog_id: Dialog ID
            
        Returns:
            Metadata for the new processing run
        """
        # Create metadata
        metadata = ProcessingRunMetadata(
            user_id=str(user_id),
            dialog_id=str(dialog_id)
        )
        
        # Create directory
        run_dir = self.get_dialog_dir(user_id, dialog_id) / f"processing_{metadata.timestamp.strftime('%Y%m%d_%H%M%S')}_{metadata.run_id}"
        run_dir.mkdir(exist_ok=True)
        
        # Save metadata
        self._save_metadata(run_dir, metadata)
        
        # Create symlink to latest
        self._update_latest_symlink(self.get_dialog_dir(user_id, dialog_id), run_dir)
        
        return metadata
    
    def _save_metadata(self, run_dir: Path, metadata: ProcessingRunMetadata) -> None:
        """Save metadata to file"""
        metadata_file = run_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write(metadata.to_json())
    
    def _update_latest_symlink(self, dialog_dir: Path, run_dir: Path) -> None:
        """Update the 'latest' symlink to point to the most recent run"""
        latest_link = dialog_dir / "latest"
        
        # Remove existing symlink if it exists
        if latest_link.exists():
            if latest_link.is_symlink():
                latest_link.unlink()
            else:
                # If it's not a symlink, something is wrong
                logger.warning(f"'latest' is not a symlink: {latest_link}")
                latest_link.unlink()
        
        # Create relative symlink
        try:
            # Use relative path for the symlink
            relative_path = os.path.relpath(run_dir, dialog_dir)
            os.symlink(relative_path, latest_link)
        except Exception as e:
            logger.error(f"Failed to create symlink: {str(e)}")
    
    def save_messages(self, run_dir: Union[str, Path], messages: List[Message]) -> None:
        """
        Save messages to file
        
        Args:
            run_dir: Processing run directory
            messages: List of messages to save
        """
        run_dir = Path(run_dir)
        messages_file = run_dir / "messages.json"
        
        # Convert messages to JSON
        messages_json = [msg.dict() for msg in messages]
        
        # Save to file
        with open(messages_file, "w") as f:
            json.dump(messages_json, f, default=str)
        
        # Update metadata
        metadata_file = run_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = ProcessingRunMetadata.from_json(f.read())
            
            metadata.mark_completed(len(messages))
            self._save_metadata(run_dir, metadata)
    
    def load_messages(self, run_dir: Union[str, Path]) -> List[Message]:
        """
        Load messages from file
        
        Args:
            run_dir: Processing run directory
            
        Returns:
            List of messages
        """
        run_dir = Path(run_dir)
        messages_file = run_dir / "messages.json"
        
        if not messages_file.exists():
            return []
        
        with open(messages_file, "r") as f:
            messages_json = json.load(f)
        
        return [Message(**msg) for msg in messages_json]
    
    def get_latest_run_dir(self, user_id: str, dialog_id: str) -> Optional[Path]:
        """
        Get the directory for the latest processing run
        
        Args:
            user_id: User ID
            dialog_id: Dialog ID
            
        Returns:
            Path to the latest run directory, or None if no runs exist
        """
        latest_link = self.get_dialog_dir(user_id, dialog_id) / "latest"
        
        if latest_link.exists() and latest_link.is_symlink():
            return latest_link.resolve()
        
        return None
    
    def get_latest_messages(self, user_id: str, dialog_id: str) -> List[Message]:
        """
        Get messages from the latest processing run
        
        Args:
            user_id: User ID
            dialog_id: Dialog ID
            
        Returns:
            List of messages from the latest run
        """
        latest_run_dir = self.get_latest_run_dir(user_id, dialog_id)
        
        if not latest_run_dir:
            return []
        
        return self.load_messages(latest_run_dir)
    
    def mark_run_failed(self, run_dir: Union[str, Path], error: str) -> None:
        """
        Mark a processing run as failed
        
        Args:
            run_dir: Processing run directory
            error: Error message
        """
        run_dir = Path(run_dir)
        metadata_file = run_dir / "metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = ProcessingRunMetadata.from_json(f.read())
            
            metadata.mark_failed(error)
            self._save_metadata(run_dir, metadata)
    
    async def cleanup_old_runs(self, max_age_days: int = 7) -> int:
        """
        Clean up old processing runs
        
        Args:
            max_age_days: Maximum age of runs to keep in days
            
        Returns:
            Number of runs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        deleted_count = 0
        
        # Iterate through all user directories
        for user_dir in self.base_dir.iterdir():
            if not user_dir.is_dir():
                continue
            
            # Iterate through all dialog directories
            for dialog_dir in user_dir.iterdir():
                if not dialog_dir.is_dir():
                    continue
                
                # Iterate through all processing run directories
                for run_dir in dialog_dir.iterdir():
                    if not run_dir.is_dir() or run_dir.name == "latest":
                        continue
                    
                    # Check if this is a processing run directory
                    if not run_dir.name.startswith("processing_"):
                        continue
                    
                    # Check metadata
                    metadata_file = run_dir / "metadata.json"
                    if not metadata_file.exists():
                        continue
                    
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = ProcessingRunMetadata.from_json(f.read())
                        
                        # Check if run is old enough to delete
                        if metadata.timestamp < cutoff_date:
                            # Don't delete if it's the latest run
                            latest_run_dir = self.get_latest_run_dir(user_dir.name, dialog_dir.name)
                            if latest_run_dir and latest_run_dir.samefile(run_dir):
                                continue
                            
                            # Delete the run directory
                            shutil.rmtree(run_dir)
                            deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error cleaning up run {run_dir}: {str(e)}")
        
        return deleted_count 