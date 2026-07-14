FROM node:20-alpine
LABEL maintainer="ZineMotion - ZICORE System"

WORKDIR /app

COPY tools/webamp/package.json .
RUN npm install --production

COPY tools/webamp/server.js .
RUN mkdir -p /app/music

EXPOSE 3002

CMD ["node", "server.js"]
