# Runtime stage with Go for building and running
FROM golang:1.25-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    python3 \
    php \
    php-cli \
    curl \
    bash

# Copy source code
COPY go.mod ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY bundles/ ./bundles/
COPY bundle.schema.json ./bundle.schema.json

# Create directories
RUN mkdir -p /app/generated /app/logs

# Set environment variables
ENV PATH="/app:${PATH}"
ENV BUNDLE_SCHEMA_URI="file:///app/bundle.schema.json"

# Download Go dependencies
RUN go mod download

# Default command
CMD ["/bin/bash"]

# Expose ports for services
EXPOSE 8080 8081 8082 8083
