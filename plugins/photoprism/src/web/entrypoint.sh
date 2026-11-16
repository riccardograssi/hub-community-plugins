#!/bin/sh
set -eu
upstream="${UPSTREAM:-http://127.0.0.1:8080}"
groups="${GROUPS_UPSTREAM:-http://photoprism-groups:8095}"
sed -e "s#__UPSTREAM__#${upstream}#g" -e "s#__GROUPS__#${groups}#g" /etc/nginx/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
