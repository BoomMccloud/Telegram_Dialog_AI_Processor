import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppThemeProvider } from './theme/ThemeContext';
import AppLayout from './components/Layout/AppLayout';
import { checkAuthentication } from './services/auth';

// Import pages
import Dashboard from './pages/Dashboard';
import Messages from './pages/Messages';
import Data from './pages/Data';
import Models from './pages/Models';
import Login from './pages/Auth/Login';

// Protected route component
interface ProtectedRouteProps {
  element: React.ReactNode;
  isAuthenticated: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  element,
  isAuthenticated
}) => {
  return isAuthenticated ? element : <Navigate to="/login" replace />;
};

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
          <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" replace />} />
          
          <Route path="/" element={
            <ProtectedRoute isAuthenticated={isAuthenticated} element={
              <AppLayout>
                <Dashboard />
              </AppLayout>
            } />
          } />
          
          <Route path="/messages" element={
            <ProtectedRoute isAuthenticated={isAuthenticated} element={
              <AppLayout>
                <Messages />
              </AppLayout>
            } />
          } />
          
          <Route path="/data" element={
            <ProtectedRoute isAuthenticated={isAuthenticated} element={
              <AppLayout>
                <Data />
              </AppLayout>
            } />
          } />
          
          <Route path="/models" element={
            <ProtectedRoute isAuthenticated={isAuthenticated} element={
              <AppLayout>
                <Models />
              </AppLayout>
            } />
          } />
        </Routes>
      </Router>
    </AppThemeProvider>
  );
}

export default App;
