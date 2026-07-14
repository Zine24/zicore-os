FROM node:20-alpine
LABEL maintainer="ZineMotion - ZICORE System"

WORKDIR /app

COPY tools/emulatorjs/package.json .
RUN npm install --production

COPY tools/emulatorjs/server.js .
RUN mkdir -p /app/roms

EXPOSE 3001

CMD ["node", "server.js"]
