FROM node:22.7
LABEL Name="My Node.js app" Version=0.2.1

WORKDIR /app

COPY src/package*.json ./
RUN npm install

COPY src/. .

# Express server is bound to Port 3000
EXPOSE 3000
ENTRYPOINT ["npm", "start"]