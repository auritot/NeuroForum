# Stage 1: Build dependencies layer
FROM python:3.12-slim as builder

WORKDIR /install

# Install system deps needed for mysqlclient + build tools
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    netcat-openbsd \
    gcc \
    libc6-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python packages into a separate directory
RUN pip install --upgrade pip && pip install --prefix=/install/packages --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install/packages /usr/local

# Copy your source code last (avoid cache busting layers early)
COPY . .

# Optional: make entrypoint executable (if used)
# COPY startup.sh /app/startup.sh
# RUN chmod +x /app/startup.sh

# ENTRYPOINT ["/app/startup.sh"]
