FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev --no-audit --no-fund

FROM node:22-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY package.json server.js ./
COPY public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
