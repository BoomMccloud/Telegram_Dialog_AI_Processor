"""
Tests for the retry utility
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.utils.retry import async_retry

@pytest.fixture
def mock_sleep():
    """Mock asyncio.sleep"""
    with patch("asyncio.sleep") as mock:
        yield mock

@pytest.mark.asyncio
async def test_retry_success(mock_sleep):
    """Test successful retry with no errors"""
    @async_retry(max_retries=3)
    async def test_func():
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert mock_sleep.call_count == 0

@pytest.mark.asyncio
async def test_retry_with_errors(mock_sleep):
    """Test retry with errors that eventually succeed"""
    attempts = 0
    
    @async_retry(max_retries=3)
    async def test_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("Temporary error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert attempts == 3
    assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_retry_max_attempts(mock_sleep):
    """Test retry with maximum attempts reached"""
    attempts = 0
    
    @async_retry(max_retries=3)
    async def test_func():
        nonlocal attempts
        attempts += 1
        raise Exception("Permanent error")
    
    with pytest.raises(Exception) as exc_info:
        await test_func()
    
    assert str(exc_info.value) == "Permanent error"
    assert attempts == 3
    assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_retry_with_custom_delay(mock_sleep):
    """Test retry with custom delay"""
    attempts = 0
    
    @async_retry(max_retries=3, delay=0.5)
    async def test_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("Temporary error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert attempts == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(0.5)  # First retry uses initial delay

@pytest.mark.asyncio
async def test_retry_with_custom_backoff(mock_sleep):
    """Test retry with custom backoff factor"""
    attempts = 0
    
    @async_retry(max_retries=3, delay=0.5, backoff=3.0)
    async def test_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("Temporary error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert attempts == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(0.5)  # First retry
    mock_sleep.assert_any_call(1.5)  # Second retry (0.5 * 3)

@pytest.mark.asyncio
async def test_retry_with_specific_exceptions(mock_sleep):
    """Test retry with specific exceptions"""
    attempts = 0
    
    @async_retry(max_retries=3, exceptions=(ValueError,))
    async def test_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert attempts == 3
    assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_retry_with_unhandled_exception(mock_sleep):
    """Test retry with unhandled exception"""
    attempts = 0
    
    @async_retry(max_retries=3, exceptions=(ValueError,))
    async def test_func():
        nonlocal attempts
        attempts += 1
        raise TypeError("Unhandled error")
    
    with pytest.raises(TypeError) as exc_info:
        await test_func()
    
    assert str(exc_info.value) == "Unhandled error"
    assert attempts == 1
    assert mock_sleep.call_count == 0

@pytest.mark.asyncio
async def test_retry_with_callback(mock_sleep):
    """Test retry with callback function"""
    attempts = 0
    callback_calls = 0
    
    def on_retry(error, attempt):
        nonlocal callback_calls
        callback_calls += 1
        assert isinstance(error, Exception)
        assert attempt == callback_calls
    
    @async_retry(max_retries=3, on_retry=on_retry)
    async def test_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("Temporary error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert attempts == 3
    assert callback_calls == 2
    assert mock_sleep.call_count == 2 