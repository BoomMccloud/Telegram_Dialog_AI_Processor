import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { initiateQRAuthentication, pollSessionStatus, devLogin } from '../../services/auth';
import { SessionStatus } from '../../types';
import PhoneAuth from '../../components/Auth/PhoneAuth';
import { api } from '../../services/api';

// Import the CSS file
import './Login.css';

interface QRCodeProps {
  qrData: string;
  onRefresh: () => void;
  expiresAt: string;
}

const QRCode: React.FC<QRCodeProps> = ({ qrData, onRefresh, expiresAt }) => {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  
  useEffect(() => {
    // Calculate time remaining
    const expiresTime = new Date(expiresAt).getTime();
    const updateTimer = () => {
      const now = new Date().getTime();
      const remaining = Math.max(0, Math.floor((expiresTime - now) / 1000));
      setTimeRemaining(remaining);
      
      if (remaining <= 0) {
        clearInterval(timerId);
      }
    };
    
    updateTimer();
    const timerId = setInterval(updateTimer, 1000);
    
    return () => clearInterval(timerId);
  }, [expiresAt]);
  
  return (
    <div className="qr-code-container">
      <img 
        src={`data:image/png;base64,${qrData}`} 
        alt="Telegram Login QR Code" 
        className="qr-code-image"
      />
      <div className="qr-code-instructions">
        <p>Scan this QR code with your Telegram app</p>
        <p>Open Telegram → Settings → Devices → Scan QR Code</p>
        <p className={timeRemaining < 30 ? 'expiring' : ''}>
          Expires in: {Math.floor(timeRemaining / 60)}:{(timeRemaining % 60).toString().padStart(2, '0')}
        </p>
        {timeRemaining <= 0 && (
          <button onClick={onRefresh} className="refresh-button">
            Generate New QR Code
          </button>
        )}
      </div>
    </div>
  );
};

enum AuthMethod {
  SELECTION = 'selection',
  QR = 'qr',
  PHONE = 'phone',
  DEV = 'dev' // Only for development
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [authMethod, setAuthMethod] = useState<AuthMethod>(AuthMethod.PHONE);
  const [qrCodeData, setQrCodeData] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [devTelegramId, setDevTelegramId] = useState<string>('');
  
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  // Get the redirect path from the location state or default to dashboard
  const getRedirectPath = () => {
    const state = location.state as { from?: string };
    return state?.from || '/';
  };
  
  const handleQRLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await initiateQRAuthentication();
      setQrCodeData(response.qr_code);
      
      // Store session ID in localStorage for potential future use
      localStorage.setItem('tempSessionId', response.session_id);
      
      setExpiresAt(response.expires_at);
      setAuthMethod(AuthMethod.QR);
      
      // Start polling
      pollSessionStatus((status, error) => {
        if (error) {
          setError('Authentication timeout. Please try again.');
          return;
        }
        
        if (status === SessionStatus.AUTHENTICATED) {
          // Ensure we have the latest token before redirecting
          api.auth.verifySession()
            .then(sessionResponse => {
              if (sessionResponse.access_token) {
                localStorage.setItem('accessToken', sessionResponse.access_token);
                if (sessionResponse.refresh_token) {
                  localStorage.setItem('refreshToken', sessionResponse.refresh_token);
                }
                console.log('[Auth Debug] Tokens updated before redirect');
              }
              navigate(getRedirectPath());
            })
            .catch(err => {
              console.error('Failed to verify session before redirect:', err);
              navigate(getRedirectPath());
            });
        }
      });
    } catch (err) {
      console.error('QR login error:', err);
      setError('Failed to generate QR code. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleDevLogin = async () => {
    if (!devTelegramId) {
      setError('Please enter a Telegram ID');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const telegramId = parseInt(devTelegramId, 10);
      const success = await devLogin(telegramId);
      
      if (success) {
        // Ensure we have the latest token before redirecting
        try {
          const sessionResponse = await api.auth.verifySession();
          if (sessionResponse.access_token) {
            localStorage.setItem('accessToken', sessionResponse.access_token);
            if (sessionResponse.refresh_token) {
              localStorage.setItem('refreshToken', sessionResponse.refresh_token);
            }
            console.log('[Auth Debug] Tokens updated before redirect (dev login)');
          }
        } catch (verifyErr) {
          console.error('Failed to verify session before redirect (dev login):', verifyErr);
        }
        navigate(getRedirectPath());
      } else {
        setError('Development login failed');
      }
    } catch (err) {
      console.error('Dev login error:', err);
      setError('Development login failed. Please check the console for details.');
    } finally {
      setLoading(false);
    }
  };
  
  const handlePhoneAuthSuccess = () => {
    // Ensure we have the latest token before redirecting
    api.auth.verifySession()
      .then(sessionResponse => {
        if (sessionResponse.access_token) {
          localStorage.setItem('accessToken', sessionResponse.access_token);
          if (sessionResponse.refresh_token) {
            localStorage.setItem('refreshToken', sessionResponse.refresh_token);
          }
          console.log('[Auth Debug] Tokens updated before redirect (phone auth)');
        }
        navigate(getRedirectPath());
      })
      .catch(err => {
        console.error('Failed to verify session before redirect (phone auth):', err);
        navigate(getRedirectPath());
      });
  };
  
  // Add function to handle switching to selection screen
  const handleShowMethodSelection = () => {
    setAuthMethod(AuthMethod.SELECTION);
    setError(null);
  };
  
  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Telegram Dialog AI Processor</h1>
        
        {error && <div className="auth-error">{error}</div>}
        
        {/* Add a link to show all authentication methods when not in selection screen */}
        {authMethod !== AuthMethod.SELECTION && (
          <div className="method-selection-link">
            <button 
              onClick={handleShowMethodSelection}
              className="text-button"
            >
              Show all login methods
            </button>
          </div>
        )}
        
        {authMethod === AuthMethod.SELECTION && (
          <div className="auth-methods">
            <h2>Choose Login Method</h2>
            <button 
              onClick={handleQRLogin} 
              disabled={loading}
              className="auth-method-btn qr"
            >
              Login with QR Code
            </button>
            <button 
              onClick={() => setAuthMethod(AuthMethod.PHONE)} 
              disabled={loading}
              className="auth-method-btn phone"
            >
              Login with Phone Number
            </button>
            
            {isDevelopment && (
              <div className="dev-login">
                <h3>Development Login</h3>
                <div className="dev-login-form">
                  <input
                    type="text"
                    placeholder="Telegram ID"
                    value={devTelegramId}
                    onChange={(e) => setDevTelegramId(e.target.value)}
                  />
                  <button 
                    onClick={handleDevLogin}
                    disabled={loading || !devTelegramId}
                  >
                    Dev Login
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {authMethod === AuthMethod.QR && qrCodeData && (
          <>
            <QRCode 
              qrData={qrCodeData} 
              onRefresh={handleQRLogin}
              expiresAt={expiresAt}
            />
            <button 
              onClick={() => setAuthMethod(AuthMethod.SELECTION)}
              className="back-button"
            >
              Back to Options
            </button>
          </>
        )}
        
        {authMethod === AuthMethod.PHONE && (
          <PhoneAuth 
            onSuccess={handlePhoneAuthSuccess}
            onCancel={() => setAuthMethod(AuthMethod.SELECTION)}
            onSwitchToQR={handleQRLogin}
          />
        )}
      </div>
    </div>
  );
};

export default Login; 