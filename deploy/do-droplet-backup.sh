#!/bin/bash

set -e

. /root/env.prod.sh

# Config
S3_BUCKET='pomdp'
S3_PREFIX='triptools/mysql-backups'

TODAY=$(date +%A)         # e.g., Monday, Tuesday
DAY=$(date +%d)           # e.g., 01, 15
MONTH=$(date +%Y-%m)

if [ "$DAY" = "01" ] || [ "$DAY" = "15" ]; then
    FILENAME="${MONTH}-${DAY}.sql.gz"
else
    FILENAME="${TODAY}.sql.gz"
fi


DUMPFILE="/tmp/${FILENAME}"

# Create dump
mysqldump -h "$TT_DB_HOST" \
          -u "$TT_DB_USER" \
          -p"$TT_DB_PASSWORD" \
          --no-tablespaces \
          --single-transaction \
          --quick \
          --skip-lock-tables \
          "$TT_DB_NAME" \
    | gzip > "$DUMPFILE"

# Upload to S3
aws s3 cp "$DUMPFILE" "s3://${S3_BUCKET}/${S3_PREFIX}/${FILENAME}"

# Cleanup
rm "$DUMPFILE"
