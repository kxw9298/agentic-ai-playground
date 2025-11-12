FROM python:3.11-slim

# Install node + npm to run the MCP filesystem server
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm -g install @modelcontextprotocol/server-filesystem \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY bridge.py /app/bridge.py

ENV HOST=0.0.0.0
ENV PORT=8765
ENV MCP_ROOT=/data

CMD ["uvicorn", "bridge:app", "--host", "0.0.0.0", "--port", "8765"]