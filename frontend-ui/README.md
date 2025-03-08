# Telegram Dialog AI Processor - Frontend

This is the frontend application for the Telegram Dialog AI Processor. It provides a user interface for managing Telegram dialogs, reviewing AI-generated responses, and configuring AI models.

## Features

- **Dashboard**: Overview of pending responses and system status
- **Messages**: Review, edit, and approve AI-generated responses
- **Data**: Select and configure Telegram dialogs for processing
- **Models**: Configure AI models and system prompts

## Technology Stack

- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Material UI**: Component library
- **React Router**: Navigation
- **Redux Toolkit**: State management
- **Axios**: API client
- **Electron**: Desktop application framework

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Clone the repository
2. Install dependencies:

```bash
npm install
```

### Development

To run the application in development mode:

```bash
# Web version
npm run dev

# Electron version
npm run electron:dev
```

### Building

To build the application for production:

```bash
# Web version
npm run build

# Electron version
npm run electron:build

# Package for all platforms
npm run electron:package
```

## Project Structure

```
frontend-ui/
├── electron/           # Electron main process
├── public/             # Static assets
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── services/       # API and other services
│   ├── store/          # Redux store and slices
│   ├── theme/          # Theme configuration
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Utility functions
│   ├── App.tsx         # Main application component
│   └── main.tsx        # Application entry point
├── package.json        # Dependencies and scripts
└── tsconfig.json       # TypeScript configuration
```

## API Integration

The application communicates with the backend API for:

- Authentication and session management
- Dialog configuration
- Response management
- Model settings

## Configuration

Environment variables can be set in a `.env` file:

```
REACT_APP_API_URL=http://localhost:8000/api
```

## Docker

The application can be run in a Docker container:

```bash
# Build the Docker image
docker build -t telegram-dialog-processor-ui .

# Run the container
docker run -p 3000:80 telegram-dialog-processor-ui
```
