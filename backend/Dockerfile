FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# Install Node.js, npm, and tools needed to install Chrome.
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

# Verify Node installation.
RUN node --version \
    && npm --version \
    && npx --version

# Install Google Chrome Stable.
RUN curl -fsSL \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
        -o /tmp/google-chrome.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome.deb \
    && rm /tmp/google-chrome.deb \
    && rm -rf /var/lib/apt/lists/*

# Confirm that Chrome exists at the path Playwright expects.
RUN google-chrome --version \
    && test -x /opt/google/chrome/chrome

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright MCP globally.
RUN npm install --global @playwright/mcp@0.0.78

# Confirm that the global MCP executable works.
RUN which playwright-mcp \
    && playwright-mcp --help

# Copy application files.
COPY . .

# Create screenshot directory.
RUN mkdir -p /app/screenshots \
    && chmod -R 777 /app/screenshots

ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]