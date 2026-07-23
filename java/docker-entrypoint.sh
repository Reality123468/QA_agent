#!/bin/bash
set -e

echo "Starting QA Agent services..."

java -jar /app/auth.jar &
java -jar /app/document.jar &
java -jar /app/chat.jar &
java -jar /app/audit.jar &

echo "All services started."
echo "  Auth:      http://0.0.0.0:${AUTH_PORT:-8080}"
echo "  Document:  http://0.0.0.0:${DOCUMENT_PORT:-8081}"
echo "  Chat:      http://0.0.0.0:${CHAT_PORT:-8082}"
echo "  Audit:     http://0.0.0.0:${AUDIT_PORT:-8083}"

wait
