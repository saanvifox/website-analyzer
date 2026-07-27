FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# Install Node.js 22 and npm.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN node --version \
    && npm --version \
    && npx --version

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright MCP globally.
RUN npm install --global --save-exact @playwright/mcp@0.0.78

# Confirm the global executable is available.
RUN which playwright-mcp \
    && playwright-mcp --help

# Install the browser expected by this MCP package.
RUN playwright-mcp install-browser chrome-for-testing

# Copy application files.
COPY . .

# Create a writable screenshots directory.
RUN mkdir -p /app/screenshots \
    && chmod -R 777 /app/screenshots

ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]