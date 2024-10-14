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
- Setup logging in app so we have complete trace of request flows
- What's the best practice when creating and providing api tokens?
  - when do we use JWT? and what are the other types of auth tokens possible?
- Every time I login with google, it shows me the notice about do I wanna allow (with same email id), which feels like a signup.
  - I guess we need to differentiate between signup and login
  - Once signed up, subsequent logins must not be showing the signup notice again. and signup attempt with the same email should simply redirect and log me into my existing account.
- Understand how the whole authentication & browser cookie thing is working. How do I adjust the cookie timeout?
- "pip install python-dotenv" (and add to requirements.txt) to automatically read .env file
- docker compose-based local setup
- understand oauth vs openid
- read everything shared by claude so far
- if I'm already authenticated, then when I open the homepage and click "login", it should directly open my dashboard (check if this is the standard practice)

## NOTES

Prompt tips:

- Give llm a persona
- Give Context, define the task + scope
- specify the output format
  - only produce dockerfile as a python string
  - hide all your other thoughts, don't output them
- if required, specify limits on output generation to keep costs under control
- If required, tell the LLM what NOT to do
- direct instructions
  - List the specific points to ensure when doing multistage
- provide examples where helpful
- (experiment) Tell LLM Make the least amount of code changes possible to achieve your goal
- (experiment) Tell the LLM to review its work after generating
- (experiment) tell llm to think its solution through, step by step
- (experiment) What to do in case the dockerfile given to llm seems incomplete or invalid or "doesn't make sense"
- TODO: Check holmesgpt prompts, other llm apps' prompts

Multistage specific tasks

- Assign a name like "build" to the first stage
- Create a new (final) stage with a slim base image (favour slim over alpine?)
- Copy the final assets (source code, node_modules, anything else applicable) into the final stage
- If the first stage contains commands related to running the app, they should be moved to the final stage
-  eg- EXPOSE, CMD, ENTRYPOINT
- Any metadata statements such as LABEL should be moved to final stage
- WORKDIR statement should be copied into the final stage


Direct prompt for multistage:
```text
You are an expert software and DevOps engineer who specializes in Docker and NodeJS backend applications.

Given a Nodejs project that contains a Docker image definition to containerize it, your goal is to reduce the size of the docker image as much as possible, while still keeping the code legible and developer-friendly.

As part of this request, your only task is to modify the given single-stage Dockerfile to adopt Multistage builds. Multistage has the benefit that the final image produced (final stage) uses a slim base image and only contains things that you put in it.
Create a final stage in the Dockerfile which only contains the application source code, its dependencies (excluding "devDependencies" from package.json) and anything else you think is necessary for the app to run or relevant to the final image.

* The final stage must use a slim base image if possible. If the previous stage uses a specific version of NodeJS, make sure to use the same version.
* If possible, set the `NODE_ENV` environment variable to `production`. This should be done BEFORE running any commands related to nodejs or npm. This ensures that dev dependencies are not installed in the final stage.
* Do a fresh install of the dependencies (node_modules) in the final stage and exclude dev dependencies. Do not change the installation commands in the previous stage and don't copy node_modules from the previous stage.
* Try to keep your code changes as consistent with the original code as possible. For example, if the previous stage uses "npm install" for installing dependencies, don't replace it with "npm ci". Try to use "install" only.
* If the previous stage contains some metadata such as LABEL statements, make sure to include them in the final stage as well, if you think its relevant.
* Comments should be added only in the new stage that you're writing. Don't add any comments in the previous stage unless you need to make an important remark.
* If the previous stage contains any `RUN` statements invoking any scripts like `npm run build`, the commands in this script will also be shared with you so you can understand its behaviour.

After writing all the code, review it step-by-step and think what the final image would contain to ensure you didn't accidentally leave out anything important.

As your response, output only the new Dockerfile, nothing else.

Optimize this Dockerfile:

"""
<DOCKERFILE CONTENTS>
"""

-- Additional details --

The `npm run build` command in the Dockerfile executes the following code (extracted from package.json):
`<build script contents>`
```

---------------------------

TODO:
- Test whole dockerfile package, fix bugs
- Handle case where env var is set as part of RUN statement ("RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y")
  - when analysing run statements, checking for NODE_ENV variable, creating new run layers, etc
  - Also other commands that can use similar syntax
- Implement AI class
- Resolve code TODO(p0) items
- Review code TODOs and resolve if needed