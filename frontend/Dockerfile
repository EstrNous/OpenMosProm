FROM node:22-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

# Всегда клонируем свежую версию без кеширования
ARG CACHEBUST=1
RUN echo "Cache bust: ${CACHEBUST}"

# Используем --no-cache для git и всегда подтягиваем последний коммит
RUN git clone --depth 1 https://github.com/AnyaZhuk/hacaton-17-19-frontend.git . && \
    git log -1 --format="%H %s" && \
    echo "Cloned at: $(date)"

RUN npm install

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80