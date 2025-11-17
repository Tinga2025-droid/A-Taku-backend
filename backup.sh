#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
cp ataku.db "backups/ataku-$STAMP.db"
find backups -type f -mtime +30 -delete
