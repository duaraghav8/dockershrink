# DockerShrink

## Development environment setup

1. Run a new PostgreSQL at localhost:5432 & PGAdmin (optional)

```shell
cd dev
docker-compose up

# test postgres
curl localhost:5432

# open pgadmin in browser - localhost:5050
# login with user = `admin@admin.com` and password = `root`
# Create new connection, use "postgres" for host

# Create a new database "dockershrink"
```

Query the database:

```sql
select * from public.user;
```

2. Set the database details (url, credentials, name, etc) in `.env`. See [env.example](./env.example).

```shell
# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Set the env vars (see file env.example)
export $(xargs <.env)

export FLASK_ENV=development

# Run the app in development using one of these commands
python3 run.py
flask --app run run
gunicorn run:app --bind localhost:5000

# Run the app in production
gunicorn run:app --bind 0.0.0.0:80

# Open the app in browser at http://localhost:5000
# NOTE: use localhost because only localhost is whitelisted by google oauth callback.
#  Any other url like 127.0.0.1 will fail during oauth login.

# To test the APIs with your token
curl -XPOST http://localhost:5000/api/v1/optimize \
  -H "Content-type: application/json" \
  -H "Authorization: <TOKEN>" \
  --data '{"Dockerfile": "FROM ubuntu", ".dockerignore": "node_modules\nnpm_debug.log", "package.json": {"version": "0.4.32"}}'

# Alternatively, run scripts inside test/
python3 test/end-to-end/end-to-end.py
```

3. After adding/modifying dependencies, update `requirements.txt`

```shell
pip freeze > requirements.txt
```

4. Run DB migrations

```shell
python -m flask db init
python -m flask db migrate -m "Initial migration"
python -m flask db upgrade

# Run subsequent migrations
python -m flask db migrate -m "What changed?"
python -m flask db upgrade
```

5. Run Black

```shell
black app
```

6. Build Docker image locally (from project root directory)

```shell
docker build -t dockershrink .
```

7. Run Docker container locally

NOTE: in host networking mode, the app port will not be accessible from outside container, even if you publish ports.

```shell
docker run --env-file .env --rm -it --net=host dockershrink
```

### Setting up the frontend

All FE assets are kept inside the `web` directory.

- `web/templates` contains HTML files which are also rendered by flask.
- `web/static` contains all static assets like js, css, etc.


1. Download the code assets from Webflow
2. Replace dummy strings inside dashboard.html with template strings so flask can render them
   - username
   - api key
3. Copy the HTML files inside `web/templates`
4. Copy all other static assets directories inside `web/static`

## TODOs
- Frontend
  - refine CLI instructions
  - Build Landing Page
- Build the CLI
- Delete and create fresh openai api key for self (current key is committed to git)
- Delete and create fresh google app for login
- deploy to a free platform to test
- Review code TODOs and resolve if needed
- Handle case where env var is set as part of RUN statement ("RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y")
  - when analysing run statements, checking for NODE_ENV variable, creating new run layers, etc
  - Also other commands that can use similar syntax
  - RunLayer/ShellCommand needs to treat the env vars correctly
  - text_pretty() needs to distribute them correctly