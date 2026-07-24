FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.28-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV DNS_RESOLVER=10.96.0.10
ENV NGINX_ENVSUBST_FILTER=^DNS_RESOLVER$
EXPOSE 80
