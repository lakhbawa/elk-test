# Use the official Node.js 18 lightweight image
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy dependency manifests first (Docker layer caching:
# npm install only re-runs when package.json changes)
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy application source code
COPY index.js ./

# Expose the port the app listens on
EXPOSE 3000

# Start the application
CMD ["node", "index.js"]
