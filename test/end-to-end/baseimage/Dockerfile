FROM node:22.7 as build
LABEL Name="My Node.js app" Version=0.2.1

WORKDIR /app

COPY src/package*.json ./
RUN npx depcheck

RUN npm install

COPY src/. .

FROM node:22.7-bookworm

WORKDIR /app

COPY package*.json .

RUN npm install --production

COPY --from=build /app/dist dist

# Express server is bound to Port 3000
EXPOSE 3000
ENTRYPOINT ["npm", "start"]
