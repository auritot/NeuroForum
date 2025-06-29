FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps for mysqlclient
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    netcat-openbsd \
    gcc \
    libc6-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Copy and set executable permission on entrypoint
# COPY startup.sh /app/startup.sh
# RUN chmod +x /app/startup.sh

# ENTRYPOINT ["/app/startup.sh"]
