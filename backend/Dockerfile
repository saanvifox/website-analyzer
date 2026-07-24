FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# Install Node.js and npm.
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

# Install Python dependencies first for better Docker caching.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright MCP locally inside /app.
# Pin the version currently appearing in your logs.
RUN npm init -y \
    && npm install --save-exact @playwright/mcp@0.0.78

# Confirm that MCP can run without downloading anything.
RUN node /app/node_modules/@playwright/mcp/cli.js --help

# The Microsoft Playwright base image already contains browser
# dependencies, but install the browser expected by this MCP version.
RUN npx playwright install chromium

COPY . .

# Ensure screenshots can be created and served by FastAPI.
RUN mkdir -p /app/screenshots

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]