FROM node:18

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Build for production
RUN npm run build

# Start the production server and bind to all network interfaces
CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"] 