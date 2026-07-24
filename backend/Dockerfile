FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# Install Node.js and npm/npx
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

# Confirm Node and npx exist during build
RUN node --version && npm --version && npx --version

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright MCP server
RUN npm install -g @playwright/mcp@latest

# Force install the exact browser MCP needs + debug output
RUN npx @playwright/mcp install-browser chrome-for-testing --force && \
    echo "=== Browser install completed ===" && \
    ls -la /root/.cache/ms-playwright || echo "Cache folder not found" && \
    npx @playwright/mcp list-browsers || echo "No list-browsers command"

# Also install regular playwright browsers as fallback
RUN npx playwright install chrome --with-deps

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]