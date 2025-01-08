package ai

import (
	"context"
	"fmt"
	"strings"

	"github.com/openai/openai-go"
)

type AIService struct {
	client *openai.Client
}

func NewAIService(client *openai.Client) *AIService {
	return &AIService{
		client: client,
	}
}

func (ai *AIService) OptimizeDockerfile(req *OptimizeRequest) (*OptimizeResponse, error) {
	userPrompt := fmt.Sprintf(_multistageUserPrompt, dockerfileContent)

	if len(scripts) > 0 {
		var scriptsDescription []string
		for i, script := range scripts {
			description := fmt.Sprintf("%d. script: `%s`\ncommands: `%s`\n", i+1, script["script"], script["commands"])
			scriptsDescription = append(scriptsDescription, description)
		}
		userPrompt += _promptNpmScriptsInvoked + strings.Join(scriptsDescription, "\n")
	}

	// *******************************************

	messages := []openai.ChatCompletionMessage{
		{
			Role:    "system",
			Content: _multistageSystemPrompt,
		},
		{
			Role:    "user",
			Content: userPrompt,
		},
	}

	chatCompletion, err := ai.client.Chat.Completions.New(context.TODO(), openai.ChatCompletionNewParams{
		Messages: openai.F([]openai.ChatCompletionMessageParamUnion{
			openai.UserMessage("Say this is a test"),
		}),
		Model: openai.F(openai.ChatModelGPT4o),
	})
	if err != nil {
		panic(err.Error())
	}

	// completion, err := ai.client.Chat.Completions.Create(messages, openaiModel)
	// if err != nil {
	// 	return "", err
	// }
	// response := completion.Choices[0].Message.Content

	// Simulate response for now
	response := "Simulated response from OpenAI"

	// *******************************************

	// gpt-4o always returns code inside backticks "```dockerfile...```".
	// We need to scrub them off and return clean dockerfile code.
	response = strings.TrimSpace(response)
	response = strings.Trim(response, "```")

	return response, nil
}

const (
	_multistageSystemPrompt = `
You are an expert software and DevOps engineer who specializes in Docker and NodeJS backend applications.

Given a Nodejs project that contains a Docker image definition to containerize it, your goal is to reduce the size of the docker image as much as possible, while still keeping the code legible and developer-friendly.

As part of this request, your only task is to modify the given single-stage Dockerfile to adopt Multistage builds.
Multistage is beneficial because the final image produced (final stage) uses a slim base image and only contains things that we put in it.
Create a final stage in the Dockerfile which only contains the application source code, its dependencies (excluding "devDependencies" from package.json) and anything else you think is necessary for the app at runtime or relevant to the final image.

* The final stage must use a slim base image if possible. If the previous stage uses a specific version of NodeJS, make sure to use the same version.
* If possible, set the ` + "`NODE_ENV`" + ` environment variable to ` + "`production`" + `. This should be done BEFORE running any commands related to nodejs or npm. This ensures that dev dependencies are not installed in the final stage.
* Do a fresh install of the dependencies (node_modules) in the final stage and exclude dev dependencies. Do not change the installation commands in the previous stage and don't copy node_modules from the previous stage.
* Try to keep your code changes as consistent with the original code as possible. For example, if the previous stage uses "npm install" for installing dependencies, don't replace it with "npm ci". Try to use "install" only.
* If the previous stage contains some metadata such as LABEL statements, make sure to include them in the final stage as well, if you think it is relevant.
* Comments should be added only in the new stage that you're writing. Don't add any comments in the previous stage unless you need to make an important remark. But don't remove any comments that already exist.
* If the previous stage contains any ` + "`RUN`" + ` statements invoking any npm scripts like ` + "`npm run build`" + `, the commands in this script will also be shared with you so you can understand its behaviour.
* Do not delete any statements originally present in the Dockerfile. If you don't understand what they're being used for (like custom scripts), just ignore them. Don't include them to the new stage.

After writing all the code, review it step-by-step and think what the final image would contain to ensure you didn't accidentally leave out anything important.

* Return only the Dockerfile code in your reply
* Do not include any additional formatting, such as markdown code blocks
`

	_multistageUserPrompt = `
Optimize this Dockerfile:

` + "```" + `
%s
` + "```"

	_promptNpmScriptsInvoked = `
-- Details of NPM scripts invoked --

NOTE:
- "script" is the npm script you see in the Dockerfile (eg- "npm run test")
- "commands" is the set of commands defined inside package.json for the particular npm script.
  For example, if package.json is ` + "`{\"scripts\": {\"test\": \"gulp .\"}}`" + `, then this field's value will be "gulp ." because the "script" invoked is "test".
- the commands for all npm scripts are extracted from package.json.

LIST OF SCRIPTS:

`
)
