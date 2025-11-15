FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# 1) Display packages for headed Chromium + noVNC
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    xvfb x11-utils x11vnc websockify novnc fluxbox \
 && rm -rf /var/lib/apt/lists/*

# 2) Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) App
COPY . .

# 4) Create data directories
RUN mkdir -p data/screenshots data/user_data_dir/playwright_context

# 5) Runtime env
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 6) Startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Health check
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /usr/local/bin/healthcheck.sh \
    && chmod +x /usr/local/bin/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

EXPOSE 8000 5901 6901
CMD ["/app/start.sh"]