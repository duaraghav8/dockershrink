# Temperature should be set to a low value, we want more deterministic, fact-based results for our tasks

_system_prompt = """
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
"""

_user_prompt = """
Optimize this Dockerfile:

```
{dockerfile}
```
"""

_user_prompt_additional_scripts = """
-- Additional Details --

{scripts}
"""


class AIService:
    def __init__(self, api_key):
        self.openai_api_key = api_key

    def add_multistage_builds(self, dockerfile: str, scripts: list):
        # Extract the dockerfile code from the response if applicable
        #   (eg- gpt 4o always returns code inside backticks "```dockerfile\n...\n```")
        pass
