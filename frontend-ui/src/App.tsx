import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppThemeProvider } from './theme/ThemeContext';
import AppLayout from './components/Layout/AppLayout';
import { checkAuthentication } from './services/auth';

// Import pages
import Dashboard from './pages/Dashboard';
import Messages from './pages/Messages';
import Data from './pages/Data';
import Models from './pages/Models';
import Login from './pages/Auth/Login';
import TelegramMessagesPage from './pages/telegram';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const authenticated = await checkAuthentication();
        setIsAuthenticated(authenticated);
      } catch (error) {
        console.error('Authentication check failed:', error);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <AppThemeProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={
            <AppLayout isAuthenticated={isAuthenticated}>
              <Dashboard />
            </AppLayout>
          } />
          
          <Route path="/messages" element={
            <AppLayout isAuthenticated={isAuthenticated}>
              <Messages />
            </AppLayout>
          } />
          
          <Route path="/telegram" element={
            <AppLayout isAuthenticated={isAuthenticated}>
              <TelegramMessagesPage />
            </AppLayout>
          } />
          
          <Route path="/data" element={
            <AppLayout isAuthenticated={isAuthenticated}>
              <Data />
            </AppLayout>
          } />
          
          <Route path="/models" element={
            <AppLayout isAuthenticated={isAuthenticated}>
              <Models />
            </AppLayout>
          } />
        </Routes>
      </Router>
    </AppThemeProvider>
  );
}

export default App;
