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

### How AI will work
TODO: evaluate this strategy - is it actually beneficial or just over engineering? Or can we just do full ai for now and introduce rules later?

Collaboration with AI is not just raw, ie, I won't just give it a dockerfile and ask it to make changes and give it back.
Instead, I'll give it the dockerfile + assets, give it a very specific goal (eg- add Multistage and ONLY stick to the following rules: slim base image + ...), give it a finite list of functions it can call on the code (eg- addLayer(3, "RUN npm install --production"), removeLayer(2), createNewStage(), etc). The AI can call a combination of these functions - return this algorithm as a response to my app.
Then the app will actually execute these functions and modify the code. The rule engine can have more control this way and ensure we're not writing something syntactically incorrect, unless the AI's thinking itself was wrong and it generated something nonsensical. 

Direct prompt for multistage:
```text
You are an expert software and DevOps engineer. I will share a nodejs REST backend code project with you. This backend runs inside Docker containers. Your goal is to optimize the docker image definition to reduce the image size as much as possible, while still keeping it developer-friendly.

Using multistage builds is a highly recommended technique to reduce the size of the final image.
Your only task is to create a final stage in this Dockerfile which only contains the application source code, dependencies and anything else you think is necessary for the app to run or relevant to the final image.
The final stage must use a slim base image if possible.
If you need more information, ask for it. For example, you want to examine the .dockerignore or the source code.
Don't make any other optimizations, just multistage builds.

Give me a new, more optimized Dockerfile and list each change you made to the file as a step. For example, if you added a new FROM statement first, you can say "1. Add new stage" and so on.

After creating the image, check it once again to make sure you didn't accidentally leave out anything important.

Here is the Dockerfile for the project.

<DOCKERFILE CONTENTS>
```

Prompt parts that may be included
```text
# I don't want this because we would certainly like to have multistage. This allows us to cherry-pick things that we want in the final stage and leave out everything else.
It is possible that the Dockerfile is already optimised with multistage build. If you think that's the case, there's no need to make any further changes.
```
