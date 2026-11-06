#!/bin/sh
set -eu
upstream="${UPSTREAM:-http://127.0.0.1:8080}"
sed "s#__UPSTREAM__#${upstream}#g" /etc/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
