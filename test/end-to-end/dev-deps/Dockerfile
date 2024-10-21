FROM node:22.7 as build
LABEL Name="My Node.js app" Version=0.2.1

WORKDIR /app

COPY src/package*.json ./

RUN npx depcheck
RUN npm install

COPY src/. .

FROM node:22.7-bookworm-slim

WORKDIR /app

COPY src/package*.json .
RUN --security=container ["npm", "install"]

# Express server is bound to Port 3000
EXPOSE 3000
ENTRYPOINT ["npm", "start"]
