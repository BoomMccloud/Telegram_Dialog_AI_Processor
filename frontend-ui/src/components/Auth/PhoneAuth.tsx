import React, { useState } from 'react';
import { initiatePhoneAuthentication, verifyPhoneCode } from '../../services/auth';

interface PhoneAuthProps {
  onSuccess: () => void;
  onCancel: () => void;
  onSwitchToQR?: () => void;
}

const PhoneAuth: React.FC<PhoneAuthProps> = ({ onSuccess, onCancel, onSwitchToQR }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [code, setCode] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [codeSent, setCodeSent] = useState(false);

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      // Format phone number if needed
      const formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : `+${phoneNumber}`;
      
      const result = await initiatePhoneAuthentication(formattedPhone);
      setSessionId(result.sessionId);
      setCodeSent(true);
    } catch (err) {
      console.error('Error sending code:', err);
      setError('Failed to send verification code. Please check your phone number and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!sessionId || !phoneNumber) {
      setError('Missing session information. Please try again.');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Format phone number if needed
      const formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : `+${phoneNumber}`;
      
      const success = await verifyPhoneCode(formattedPhone, code, sessionId);
      
      if (success) {
        onSuccess();
      } else {
        setError('Verification failed. Please check the code and try again.');
      }
    } catch (err) {
      console.error('Error verifying code:', err);
      setError('Failed to verify code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="phone-auth-container">
      <h2>{codeSent ? 'Verify Code' : 'Login with Phone'}</h2>
      
      {error && <div className="auth-error">{error}</div>}
      
      {!codeSent ? (
        <form onSubmit={handleSendCode}>
          <div className="form-group">
            <label htmlFor="phoneNumber">Phone Number (with country code)</label>
            <input
              id="phoneNumber"
              type="tel"
              placeholder="e.g. +15551234567"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
            <small>Enter your phone number with country code (e.g. +1 for US)</small>
          </div>
          
          <div className="buttons">
            <button type="button" onClick={onCancel} disabled={loading}>
              Back
            </button>
            <button type="submit" disabled={loading || !phoneNumber}>
              {loading ? 'Sending...' : 'Send Code'}
            </button>
          </div>
          
          {onSwitchToQR && (
            <div className="alternative-login">
              <p>Having trouble with phone authentication?</p>
              <button 
                type="button" 
                onClick={onSwitchToQR}
                className="text-button"
                disabled={loading}
              >
                Try QR Code Login
              </button>
            </div>
          )}
        </form>
      ) : (
        <form onSubmit={handleVerifyCode}>
          <div className="form-group">
            <label htmlFor="code">Verification Code</label>
            <input
              id="code"
              type="text"
              placeholder="Enter code from Telegram"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
            />
            <small>Enter the verification code sent to your Telegram account</small>
          </div>
          
          <div className="buttons">
            <button 
              type="button" 
              onClick={() => setCodeSent(false)} 
              disabled={loading}
            >
              Back
            </button>
            <button type="submit" disabled={loading || !code}>
              {loading ? 'Verifying...' : 'Verify Code'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default PhoneAuth; 