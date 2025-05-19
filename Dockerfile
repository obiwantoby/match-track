# Fix for proxy_pass to backend
RUN sed -i 's|proxy_pass http://localhost:8001/;|proxy_pass http://127.0.0.1:8001/;|g' /etc/nginx/nginx.conf