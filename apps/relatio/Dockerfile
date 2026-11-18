# Imagen de Cloud Run para apps/relatio. Node 22 corre TypeScript directo (sin paso de build).
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production PORT=8080
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY src ./src
RUN addgroup -S app && adduser -S app -G app
USER app
EXPOSE 8080
CMD ["node", "src/servidor.ts"]
