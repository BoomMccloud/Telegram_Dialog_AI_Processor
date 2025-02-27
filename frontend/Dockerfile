FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose the port
EXPOSE 3000

# Command to run the application
CMD ["npm", "start"] 