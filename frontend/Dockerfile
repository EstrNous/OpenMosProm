FROM node:22-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

RUN git clone https://github.com/AnyaZhuk/hacaton-17-19-frontend.git .

RUN npm install

RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY ./nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80