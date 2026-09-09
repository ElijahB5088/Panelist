#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    chown -R panelist:panelist /app/data
    exec gosu panelist "$@"
else
    exec "$@"
fi