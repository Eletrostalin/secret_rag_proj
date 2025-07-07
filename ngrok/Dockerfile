FROM alpine

RUN apk add --no-cache curl tar

RUN curl -L https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -o /tmp/ngrok.tgz \
    && tar -C /usr/local/bin -xzf /tmp/ngrok.tgz \
    && chmod +x /usr/local/bin/ngrok

ENTRYPOINT ["ngrok"]
