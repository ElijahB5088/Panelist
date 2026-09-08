#!/bin/sh
set -eu

chown -R panelist:panelist /app/data
exec gosu panelist "$@"