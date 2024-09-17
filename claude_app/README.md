# DockerShrink

Setup fresh local development environment

1. Run a new PostgreSQL at localhost:5432 & PGAdmin (optional)
2. Set the database details (url, credentials, name, etc) in `.env`.

```shell
# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Set the env vars
export $(xargs <.env)
export FLASK_ENV=development

# Run the app
python3 run.py

# Open the app in browser at http://localhost:5000
# NOTE: use localhost because only localhost is whitelisted by google oauth callback.
#  Any other url like 127.0.0.1 will fail during oauth login.
```

To update `requirements.txt`

```shell
pip freeze > requirements.txt
```

Run DB migrations

```shell
python -m flask db init
python -m flask db migrate -m "Initial migration"
python -m flask db upgrade
```

## TODO
- "pip install python-dotenv" (and add to requirements.txt) to automatically read .env file
- docker compose-based local setup
- understand oauth vs openid
- read everything shared by claude so far
- try the other apis of the app
