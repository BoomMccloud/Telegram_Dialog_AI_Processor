import React, { useState } from 'react';
import { 
  Box, 
  AppBar, 
  Toolbar, 
  Typography, 
  IconButton, 
  Button,
  Container,
  Menu,
  MenuItem,
  useTheme,
  useMediaQuery,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Message as MessageIcon,
  Storage as StorageIcon,
  Psychology as PsychologyIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
} from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import { useThemeContext } from '../../theme/ThemeContext';

// Navigation items
const navItems = [
  { name: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { name: 'Messages', path: '/messages', icon: <MessageIcon /> },
  { name: 'Data', path: '/data', icon: <StorageIcon /> },
  { name: 'Models', path: '/models', icon: <PsychologyIcon /> },
];

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const theme = useTheme();
  const { mode, toggleColorMode } = useThemeContext();
  const location = useLocation();
  
  // Mobile menu state
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileMenuAnchorEl, setMobileMenuAnchorEl] = useState<null | HTMLElement>(null);
  const isMobileMenuOpen = Boolean(mobileMenuAnchorEl);
  
  const handleMobileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMobileMenuAnchorEl(event.currentTarget);
  };

  const handleMobileMenuClose = () => {
    setMobileMenuAnchorEl(null);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="fixed">
        <Toolbar>
          <Typography 
            variant="h6" 
            noWrap 
            component="div" 
            sx={{ 
              mr: 2,
              display: { xs: 'none', sm: 'flex' },
              fontWeight: 600
            }}
          >
            Telegram Dialog AI Processor
          </Typography>
          
          <Typography 
            variant="h6" 
            noWrap 
            component="div" 
            sx={{ 
              flexGrow: 1,
              display: { xs: 'flex', sm: 'none' },
              fontWeight: 600
            }}
          >
            TG Dialog AI
          </Typography>

          {/* Desktop navigation */}
          <Box sx={{ 
            flexGrow: 1, 
            display: { xs: 'none', md: 'flex' },
            ml: 2
          }}>
            {navItems.map((item) => {
              const isActive = location.pathname === item.path || 
                (item.path !== '/' && location.pathname.startsWith(item.path));
                
              return (
                <Button
                  key={item.name}
                  component={Link}
                  to={item.path}
                  sx={{
                    mx: 1,
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    fontWeight: isActive ? 'bold' : 'normal',
                    borderBottom: isActive ? '3px solid white' : 'none',
                    borderRadius: 0,
                    paddingBottom: isActive ? '5px' : '8px',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.1)',
                      borderBottom: !isActive ? '3px solid rgba(255, 255, 255, 0.3)' : '3px solid white',
                      paddingBottom: '5px',
                    }
                  }}
                  startIcon={item.icon}
                >
                  {item.name}
                </Button>
              );
            })}
          </Box>

          {/* Theme toggle button */}
          <Tooltip title={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}>
            <IconButton color="inherit" onClick={toggleColorMode}>
              {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
            </IconButton>
          </Tooltip>

          {/* Mobile menu button */}
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open menu"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMobileMenuOpen}
              edge="end"
            >
              <MenuIcon />
            </IconButton>
          )}
        </Toolbar>
      </AppBar>

      {/* Mobile menu */}
      <Menu
        id="menu-appbar"
        anchorEl={mobileMenuAnchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={isMobileMenuOpen}
        onClose={handleMobileMenuClose}
      >
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/' && location.pathname.startsWith(item.path));
          
          return (
            <MenuItem 
              key={item.name} 
              component={Link} 
              to={item.path}
              onClick={handleMobileMenuClose}
              selected={isActive}
              sx={{
                fontWeight: isActive ? 'bold' : 'normal',
                '&.Mui-selected': {
                  backgroundColor: theme.palette.primary.main + '20',
                },
              }}
            >
              <Box sx={{ mr: 2, color: isActive ? theme.palette.primary.main : 'inherit' }}>
                {item.icon}
              </Box>
              {item.name}
            </MenuItem>
          );
        })}
        <Divider />
        <Box sx={{ p: 2, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Version 0.1.0
          </Typography>
        </Box>
      </Menu>

      {/* Main content */}
      <Box 
        component="main" 
        sx={{ 
          flexGrow: 1, 
          p: 3,
          mt: 8, // Add margin top to account for AppBar height
        }}
      >
        <Container maxWidth="xl">
          {children}
        </Container>
      </Box>
    </Box>
  );
};

export default AppLayout; 