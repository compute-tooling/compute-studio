import os

host = os.environ.get("REDIS_HOST")
port = os.environ.get("REDIS_PORT")
password = os.environ.get("REDIS_PASSWORD", None)
REDIS_URL = f"redis://:{password}@{host}:{port}/"
