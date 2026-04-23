# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source code
COPY src/ ./src/

# Build the application
RUN cd src && go build -o /app/bundle-runner bundle.go

# Runtime stage
FROM golang:1.21-alpine

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    python3 \
    php \
    php-cli \
    curl \
    bash

# Copy built binary from builder
COPY --from=builder /app/bundle-runner /app/bundle-runner

# Copy source code for runtime
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
