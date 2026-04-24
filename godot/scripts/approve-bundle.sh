#!/usr/bin/env bash
# Human-in-the-loop CLI for approving/rejecting WORKFLOW_BUNDLE in bundles/pending/.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PENDING_DIR="$ROOT/bundles/pending"
APPROVED_DIR="$ROOT/bundles/approved"
REJECTED_DIR="$ROOT/bundles/rejected"

mkdir -p "$PENDING_DIR" "$APPROVED_DIR" "$REJECTED_DIR"

ACTION="${1:-list}"
BUNDLE="${2:-}"

usage() {
    echo "Usage: $0 {list|approve|reject} [bundle-name]"
    echo "  list    — list all pending bundles"
    echo "  approve — move bundle from pending → approved"
    echo "  reject  — move bundle from pending → rejected"
    exit 1
}

list_pending() {
    local count=0
    for f in "$PENDING_DIR"/*.json; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        kind=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('kind','?'))" "$f" 2>/dev/null || echo "?")
        desc=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('description','no desc'))" "$f" 2>/dev/null || echo "no desc")
        printf "  %-40s %-20s %s\n" "$name" "$kind" "$desc"
        ((count++)) || true
    done
    echo "Total pending: $count"
}

approve() {
    if [ -z "$BUNDLE" ]; then
        echo "Error: bundle name required"
        usage
    fi
    src="$PENDING_DIR/$BUNDLE"
    dst="$APPROVED_DIR/$BUNDLE"
    if [ ! -f "$src" ]; then
        echo "Error: not found in pending: $BUNDLE"
        exit 1
    fi
    mv "$src" "$dst"
    echo "✓ Approved: $BUNDLE → $dst"
}

reject() {
    if [ -z "$BUNDLE" ]; then
        echo "Error: bundle name required"
        usage
    fi
    src="$PENDING_DIR/$BUNDLE"
    dst="$REJECTED_DIR/$BUNDLE"
    if [ ! -f "$src" ]; then
        echo "Error: not found in pending: $BUNDLE"
        exit 1
    fi
    mv "$src" "$dst"
    echo "✗ Rejected: $BUNDLE → $dst"
}

case "$ACTION" in
    list)  list_pending ;;
    approve) approve ;;
    reject) reject ;;
    *) echo "Unknown action: $ACTION"; usage ;;
esac
