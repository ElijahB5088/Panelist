#!/bin/sh
set -eu

chown -R panelist:panelist /app/data
exec su -s /bin/sh panelist -c 'exec "$@"' -- "$@"