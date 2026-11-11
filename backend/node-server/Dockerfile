
FROM node:20-slim

WORKDIR /app

COPY backend/node-server/package*.json ./

RUN npm ci --omit=dev

COPY backend/node-server/src ./src

EXPOSE 3000

CMD ["npm", "start"]
