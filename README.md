# DockerShrink

![Typical interaction with dockershrink CLI](./assets/images/dockershrink-how-it-works.gif)

**Dockershrink is an Open Source Commandline Tool that helps you reduce the size of your Docker images.**

It combines the power of traditional Rule-based analysis with Generative AI to apply state-of-the-art optimizations to your Image configurations :brain:

Dockershrink can automatically apply techniques like Multi-Stage builds, switching to Lighter base images like alpine and running dependency checks. PLUS a lot more is on the roadmap :rocket:

Currently, the tool only works for [NodeJS](https://nodejs.org/en) applications.


> [!IMPORTANT]
> Dockershrink is **BETA** software.
> 
> We would love to hear what you think! You can provide your feedback by [Creating an Issue](https://github.com/duaraghav8/dockershrink-cli/issues) in this repository.


## Why does dockershrink exist?
Every org using containers in development or production environments understands the pain of managing hundreds or even thousands of BLOATED Docker images in their infrastructure.

But not everyone realizes that by just implementing some basic techniques, they can reduce the size of a 1GB Docker image down to **as little as 100 MB**!

([I also made a video on how to do this.](https://youtu.be/vHBHxQfK6cM))

Imagine the costs saved in storage & data transfer, decrease in build times AND the productivity gains for developers :exploding_head:

Dockershrink aims to auomatically apply advanced optimization techniques such as Multistage builds, Light base images, removing unused dependencies, etc. so that developers & devops engineers don't have to waste time doing so and everybody still reaps the benefits!

You're welcome :wink:



## How it works
Currently, the CLI is the primary way to interact with dockershrink.

When you invoke it on your project, it analyzes code files.

Currently, the files Dockershrink looks for are:

:point_right: `Dockerfile` (Required)

:point_right: `package.json` (Optional)

:point_right: `.dockerignore` (Optional, created if doesn't already exist)

It then creates a new directory (default name: `dockershrink.optimized`) inside the project, which contains modified versions of your files that will result in a smaller Docker Image.

The CLI outputs a list of actions it took over your files.

It may also include suggestions on further improvements you could make.


## Installation
**TODO**


## Usage

Navigate into the root directory of one of your Node.js projects and run a simple command:

```bash
dockershrink optimize
```

Dockershrink will create a new directory with the optimized files and output the actions taken and (maybe) some more suggestions.

For more information on the `optimize` command, run
```bash
dockershrink help optimize
```


### Using AI Features

> [!NOTE]
> Using AI features is optional, but **highly recommended** for more customized and powerful optimizations.
>
> Currently, you need to supply your own openai api key, so even though Dockershrink itself is free, openai usage might incur some cost for you.

By default, dockershrink only runs rule-based analysis to optimize your image definition.

If you want to enable AI, you must supply your own [OpenAI API Key](https://openai.com/index/openai-api/).

```bash
dockershrink optimize --openai-api-key <your openai api key>

# Alternatively, you can supply the key as an environment variable
export OPENAI_API_KEY=<your openai api key>
dockershrink optimize
```

> [!NOTE]
> Dockershrink does not store your OpenAI API Key.
>
> So you must provide your key every time you want "optimize" to enable AI features.

### Default file paths
By default, the CLI looks for the files to optimize in the current directory.

You can also specify the paths to all files using options (see `dockershrink help optimize` for the available options).


## Development


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

# To setup a new Database:
export DATABASE_URL=...
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
   - api key quotes
3. If links are incorrect fix them.
   - "index.html" -> "/"
   - "dashboard.html" -> "/dashboard"
4. Copy the HTML files inside `web/templates`
5. Copy all other static assets directories inside `web/static`

## TODO (p0)
- (TBD) FIX the "basic" test case (we show this in landing page)
  - basic case: single stage which installs dependencies -> copies code into image -> runs the app
  - for basic case, there is NO need for multistage build so don't force it. non-ai already works fine for basic, but ai messes it up.
  - Level 2 case is: user is doing some additional stuff in basic (like run tests). In this case, we should put multistage builds.
  - the final stage of an image should only install prod deps + copy code + run app. If the first stage is only doing this, there's no need for multistage.
  - the moment we can determine that a single-stage image does NOT need multistage, we can apply the rest of our optimizations in that single stage itself!
  - Strategies:
    - Tell the LLM to NOT add multistage if stage 1 only does the 3 essential steps. Then handle this in response.
    - Programmatically determine whether multi is needed (not sure if possible)
  - COUNTER ARG: we are adding "npx depcheck" in the original stage in case we add multistage, so multistage is justified
- LAUNCH
  - Test end-to-end
    - Installation
    - All binaries working on respective platforms
    - Authentication (init)
    - optimize
    - Homepage, User Dashboard
  - start reaching out to people

## TODO
- Review code TODOs and resolve if needed
- Handle case where env var is set as part of RUN statement ("RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y")
  - when analysing run statements, checking for NODE_ENV variable, creating new run layers, etc
  - Also other commands that can use similar syntax
  - RunLayer/ShellCommand needs to treat the env vars correctly
  - text_pretty() needs to distribute them correctly
