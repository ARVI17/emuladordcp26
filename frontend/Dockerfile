FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
COPY package*.json ./
RUN npm ci
COPY . .
ARG BUILD_REVISION=unknown
ARG BUILD_DATE=unknown
ARG BUILD_ENVIRONMENT=development
ARG BUILD_DIRTY=false
ENV BUILD_REVISION=$BUILD_REVISION BUILD_DATE=$BUILD_DATE BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT BUILD_DIRTY=$BUILD_DIRTY
RUN npm run build

FROM nginx:1.27-alpine
ARG BUILD_REVISION=unknown
ARG BUILD_DATE=unknown
ARG BUILD_ENVIRONMENT=development
ARG BUILD_DIRTY=false
LABEL org.opencontainers.image.revision=$BUILD_REVISION org.opencontainers.image.created=$BUILD_DATE app.edition=FC27 app.environment=$BUILD_ENVIRONMENT app.source_dirty=$BUILD_DIRTY
RUN sed -i -E 's/^worker_processes[[:space:]]+auto;/worker_processes 1;/' /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
