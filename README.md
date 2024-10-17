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

2. Set the database details (url, credentials, name, etc) in `.env`.

```shell
# Create new virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Set the env vars (see file env.example)
export $(xargs <.env)
export FLASK_ENV=development

# Run the app
python3 run.py

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
```

5. Run Black

```shell
black app
```

## TODO
- if I'm already authenticated, then when I open the homepage and click "login", it should directly open my dashboard (check if this is the standard practice)
- Every time I login with google, it shows me the notice about do I wanna allow (with same email id), which feels like a signup.
  - I guess we need to differentiate between signup and login
  - Once signed up, subsequent logins must not be showing the signup notice again. and signup attempt with the same email should simply redirect and log me into my existing account.
- Understand how the whole authentication & browser cookie thing is working. How do I adjust the cookie timeout?
- Setup logging in app so we have complete trace of request flows
- What's the best practice when creating and providing api tokens?
  - when do we use JWT? and what are the other types of auth tokens possible?
- "pip install python-dotenv" (and add to requirements.txt) to automatically read .env file
- docker compose-based local setup
- understand oauth vs openid
- read everything shared by claude so far


TODO:
- productionize the backend
- end to end testing
- Review code TODOs and resolve if needed
- Handle case where env var is set as part of RUN statement ("RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y")
  - when analysing run statements, checking for NODE_ENV variable, creating new run layers, etc
  - Also other commands that can use similar syntax
  - RunLayer/ShellCommand needs to treat the env vars correctly
  - text_pretty() needs to distribute them correctly