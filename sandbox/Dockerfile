FROM node:24.21.0-bookworm-slim
USER root
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl tree python3 \
    && rm -rf /var/lib/apt/lists/*
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
COPY checks/package.json checks/package-lock.json /opt/webbuilder-checks/
RUN cd /opt/webbuilder-checks && npm ci --no-audit --no-fund \
    && npx playwright install --with-deps --only-shell chromium \
    && chmod -R a+rX /opt/webbuilder-checks /opt/pw-browsers
WORKDIR /home/user/react-app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY src/ /home/user/react-app/src/
COPY vite.config.ts tsconfig.json index.html .oxlintrc.json .gitignore README.md ./
RUN chown -R user:user /home/user/react-app && npm cache clean --force
USER user
