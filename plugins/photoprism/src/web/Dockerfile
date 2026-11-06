FROM nginx:1.27-alpine
COPY clients/web /usr/share/nginx/html
COPY src/web/default.conf.template /etc/nginx/default.conf.template
COPY src/web/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
