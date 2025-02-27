# Telegram Dialog AI Processor - Docker Setup

This document provides instructions for setting up and running the Telegram Dialog AI Processor using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed on your system
- Telegram API credentials (API ID and API Hash)

## Setup Instructions

1. **Clone the repository**

```bash
git clone <repository-url>
cd Telegram_Dialog_AI_Processor
```

2. **Configure environment variables**

Copy the example environment file and update it with your Telegram API credentials:

```bash
cp .env.docker .env
```

Edit the `.env` file and replace the placeholder values with your actual Telegram API credentials:

```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

3. **Build and start the containers**

```bash
docker-compose up -d
```

This command will:
- Start a PostgreSQL database
- Build and start the backend FastAPI application
- Build and start the frontend Next.js application
- Initialize the database schema if it doesn't exist

4. **Access the application**

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Container Management

### View container logs

```bash
# View logs for all containers
docker-compose logs

# View logs for a specific container
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
```

### Stop the containers

```bash
docker-compose down
```

### Stop and remove volumes (will delete all data)

```bash
docker-compose down -v
```

### Rebuild containers after code changes

```bash
docker-compose up -d --build
```

## Database Management

The PostgreSQL database is accessible at `localhost:5432` with the following default credentials:
- Username: postgres
- Password: postgres
- Database: telegram_dialog

You can connect to it using any PostgreSQL client.

### Database Migrations

The database schema is automatically created when the backend container starts. If you need to make changes to the schema, you'll need to update the initialization script in `backend/app/db/init_db.py`.

## Troubleshooting

### Backend container fails to start

Check the logs for the backend container:

```bash
docker-compose logs backend
```

Common issues:
- PostgreSQL is not ready yet (the backend will retry automatically)
- Invalid Telegram API credentials
- Port 8000 is already in use on your host machine

### Frontend container fails to start

Check the logs for the frontend container:

```bash
docker-compose logs frontend
```

Common issues:
- Port 3000 is already in use on your host machine
- Build errors in the Next.js application

### Database connection issues

Check the logs for the PostgreSQL container:

```bash
docker-compose logs postgres
```

Common issues:
- PostgreSQL is still initializing
- Incorrect database credentials in the environment variables 