# Basic case only contains 3 main steps:
# - install dependencies
# - copy code
# - run the app
#
# This is the minimum amount of stuff required to dockerize a node app

FROM node:22.7

WORKDIR /app

COPY package*.json .
RUN npm install

COPY src/. .

EXPOSE 3000
ENTRYPOINT ["npm", "start"]
