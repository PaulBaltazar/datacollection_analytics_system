FROM node:22-alpine AS deps
WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund

FROM node:22-alpine
ENV NODE_ENV=production
WORKDIR /app

# Runtime starts with node directly, so npm and yarn are unnecessary.
RUN rm -rf /usr/local/lib/node_modules/npm \
           /opt/yarn-* \
    && rm -f /usr/local/bin/npm \
             /usr/local/bin/npx \
             /usr/local/bin/yarn \
             /usr/local/bin/yarnpkg

COPY --from=deps /app/node_modules ./node_modules
COPY package.json server.js ./
COPY public ./public

USER node
EXPOSE 3000

CMD ["node", "server.js"]