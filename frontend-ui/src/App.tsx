import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppThemeProvider } from './theme/ThemeContext';
import AppLayout from './components/Layout/AppLayout';

// Import pages
import Dashboard from './pages/Dashboard';
import Messages from './pages/Messages';
import Data from './pages/Data';
import Models from './pages/Models';

function App() {
  return (
    <AppThemeProvider>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/messages" element={<Messages />} />
            <Route path="/data" element={<Data />} />
            <Route path="/models" element={<Models />} />
          </Routes>
        </AppLayout>
      </Router>
    </AppThemeProvider>
  );
}

export default App;
