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

## TODO (p0)
- Frontend
    - Build Landing Page
  - refine CLI instructions
- Build the CLI
- Delete and create fresh openai api key for self (current key is committed to git)
- Delete and create fresh google app for login
- deploy to render

## TODO
- Review code TODOs and resolve if needed
- Handle case where env var is set as part of RUN statement ("RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y")
  - when analysing run statements, checking for NODE_ENV variable, creating new run layers, etc
  - Also other commands that can use similar syntax
  - RunLayer/ShellCommand needs to treat the env vars correctly
  - text_pretty() needs to distribute them correctly


### CLI generation prompt
You are an expert software engineer who specialises in build websites (frontends and backends) and system tooling.

I've created a SaaS website that allows people to reduce the size of their NodeJS Docker images by simply uploading their project files.
User uploads project files -> platform modifies the files to use best practices -> platform returns modified files back to user.
The product is called Dockershrink.

Your task is to create a commandline application - which is the main client-side interface through which the user will interact with my platform.

Requirements:
* Create the CLI in Golang
* CLI name should be dockershrink, so I invoke it on the commandline by calling `dockershrink`.
* All code testing and build should occur inside a Docker container.
* The application binaries should be created for MacOS, Windows and Linux for amd and arm CPU architectures. It should also be able to run on macs with M-series chips.
* By default, the CLI should communicate with the web server `https://dockershrink.com`. But server address should be configurable by supplying the environment variable `SERVER_URL`.
* Also create a `README.md` which contains instructions on how to compile the code into the final executables for all platforms. Document the whole CLI in this README: its purpose, usage, basic architecture, etc.

Below is the description of how the CLI can be used:

1. Print a help message, which shows the complete usage of the CLI
```shell
dockershrink help
dockershrink --help
```

2. Initialise the CLI
Once a user downloads the CLI, they must first initialise it by adding their API key that they get from my platform. Without the key, the CLI cannot make authenticated requests to the backend.
Internally, the cli should store this api key in a configuration file in the home directory of the user (eg- `~/.dsconfig.json`).

```shell
# --api-key is mandatory
dockershrink init --api-key <api key>
```

3. Run dockershrink over a project
This is where the user begins using dockershrink. They navigate to the root directory of their nodejs project and invoke the cli.

The cli collects certain files from the project, sends them to the backend API and gets back a response from it.
These files are:
a. `Dockerfile` - cli looks for it in the current directory by default. The user can also explicitly specify its path using the `--dockerfile` option. If this file is not found, cli does not include it in the api request.
b. `.dockerignore` - cli looks for it in the current directory by default. The user can also explicitly specify its path using the `--dockerignore` option. If this file is not found, cli does not include it in the api request.
c. `package.json` - cli looks for it in the current directory by default. If there's a `src` directory, cli also tries to look for the file inside it. The user can also explicitly specify its path using the `--package-json` option. If this file is not found, cli does not include it in the api request.

NOTE: This is an authenticated API, so the cli must supply the user's API key in the `Authorization` header as part of its api request.

NOTE: If this command is invoked and the user's api key is not configured, output an error message telling the user to first configure their api key using `init`.

```shell
# Simply invoking the cli will trigger main functionality
dockershrink

# User can optionally provide their openai API key to enable AI features
# Alternatively, they can set the environment variable `OPENAI_API_KEY`.
dockershrink --openai-api-key <openai api key> 

# User can optionally specify exact paths to files
dockershrink --dockerfile ./Dockerfile --dockerignore ./.dockerignore --package-json ./src/package.json
```

How to call the API:
- cli will make a `POST` HTTP request to `/api/v1/optimize` api
- following is the complete JSON data that can be sent to the API:
```json
{
  "Dockerfile": "<contents of the Dockerfile file if supplied>",
  ".dockerignore": "<contents of the .dockerfile file if supplied>",
  "package.json": "<contents of the package.json file if supplied>",
  "openai_api_key": "user's openai api key if supplied"
}
```

Handling the API Response:

A successful api request returns the following JSON response:
```json
{
  "modified_project": {
    ".dockerignore": "<contents of new .dockerignore file>",
    "Dockerfile": "<contents of new Dockerfile>"
  },
  "actions_taken": [
    {
      "filename": "<name of the file in which this change was made>",
      "title": "<summary of the change made>",
      "description": "<detailed description of the change made>",
      "rule": "name of the rule"
    }
  ],
  "recommendations": [
    {
      "filename": "<name of the file in which this change was made>",
      "title": "<summary of the change made>",
      "description": "<detailed description of the change made>",
      "rule": "name of the rule"
    }
  ]
}
```

-> `modified_project` is an object that contains all the files produced by the platform.
Key is the filename, value is the contents of that file.
The cli must add these files inside the project in a new directory called `dockershrink.optimised`.
-> `actions_taken` is a list of modifications made by the backend to optimise the user-provided files. All keys will be present in an object. cli should display these actions as output to the user. 
-> `recommendations` is a list of modifications that the backend recommends the user to make. All keys will be present in an object. cli should display recommendations as output.


If the request is unsuccessful, the api sends the error http status code and the following JSON object:
```json
{
  "error": "<error message>"
}
```
Cli should display the error message to the user.


When in doubt, don't assume anything. Ask me clarifying questions instead.
Before generating code, tell me what you plan on doing in bullet-point format.

Once I approve your plan, go ahead and generate the code.