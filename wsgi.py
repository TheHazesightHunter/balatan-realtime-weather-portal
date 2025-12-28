from app import app
from werkzeug.middleware.proxy_fix import ProxyFix

# Trust 1 proxy for proto and host headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

if __name__ == "__main__":
    app.run()
