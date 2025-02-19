package ai

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"strings"

	"github.com/duaraghav8/dockershrink/internal/ai/promptcreator"
	"github.com/duaraghav8/dockershrink/internal/dockerfile"
	"github.com/openai/openai-go"
)

// OptimizeDockerfile optimizes the given Dockerfile using OpenAI GPT-4o
// It returns the optimized Dockerfile along with the actions taken and
// recommendations for further optimization.
func (ai *AIService) OptimizeDockerfile(req *OptimizeRequest) (*OptimizeResponse, error) {
	systemInstructions, err := ai.constructOptimizeSystemInstructions(req)
	if err != nil {
		return nil, fmt.Errorf("failed to construct system prompt: %w", err)
	}
	userQuery, err := ai.constructOptimizeUserQuery(req)
	if err != nil {
		return nil, fmt.Errorf("failed to construct user prompt: %w", err)
	}

	ai.L.Debug("Sending user message to LLM", map[string]string{"prompt": userQuery})

	messages := []openai.ChatCompletionMessageParamUnion{
		openai.SystemMessage(systemInstructions),
		openai.UserMessage(userQuery),
	}
	responseFormat := openai.ResponseFormatJSONSchemaJSONSchemaParam{
		Name:        openai.F("modifications"),
		Description: openai.F("Optimized assets for the project along with the actions taken and further recommendations"),
		Schema:      openai.F(optimizeResponseSchema),
		Strict:      openai.Bool(true),
	}
	params := openai.ChatCompletionNewParams{
		Messages: openai.F(messages),
		Tools:    openai.F(availableTools),
		ResponseFormat: openai.F[openai.ChatCompletionNewParamsResponseFormatUnion](
			openai.ResponseFormatJSONSchemaParam{
				Type:       openai.F(openai.ResponseFormatJSONSchemaTypeJSONSchema),
				JSONSchema: openai.F(responseFormat),
			},
		),
		Model: openai.F(OpenAIPreferredModel),
	}

	for i := 0; i < MaxLLMCalls; i++ {
		ai.L.Debug(
			"Agentic Loop: Calling LLM",
			map[string]string{
				"attempt": fmt.Sprintf("#%d", i+1),
			},
		)

		response, err := ai.client.Chat.Completions.New(context.Background(), params)
		if err != nil {
			return nil, fmt.Errorf("failed to get chat completion: %w", err)
		}

		ai.L.Debug("Received response from LLM", map[string]string{
			"content": response.Choices[0].Message.Content,
			"json":    response.Choices[0].Message.JSON.RawJSON(),
		})

		toolCalls := response.Choices[0].Message.ToolCalls
		if len(toolCalls) == 0 {
			ai.L.Debug("Response contains final optimized assets", nil)

			optimizeResponse := OptimizeResponse{}
			err = json.Unmarshal([]byte(response.Choices[0].Message.Content), &optimizeResponse)
			if err != nil {
				return nil, fmt.Errorf("failed to parse final response from LLM: %w", err)
			}

			// TODO: also log the actions taken and recommendations
			ai.L.Debug(
				"Unpacked LLM Response",
				map[string]string{
					"dockerfile": optimizeResponse.Dockerfile,
				},
			)

			ok, err := dockerfile.Validate(optimizeResponse.Dockerfile)
			if !ok {
				data := map[string]string{
					"error": err.Error(),
				}
				ai.L.Debug("LLM returned an invalid Dockerfile", data)

				feedback, _ := promptcreator.ConstructPrompt(InvalidDockerfileInResponsePrompt, data)
				params.Messages.Value = append(params.Messages.Value, openai.SystemMessage(feedback))
				continue
			}

			return &optimizeResponse, nil
		} else {
			ai.L.Debug("LLM has called tool(s)", map[string]string{
				"message": response.Choices[0].Message.Content,
			})

			// add the tool call message back to the ongoing conversation with LLM
			params.Messages.Value = append(params.Messages.Value, response.Choices[0].Message)

			for _, toolCall := range toolCalls {
				if toolCall.Function.Name == ToolReadFiles {
					var extractedParams struct {
						Filepaths []string `json:"filepaths"`
					}
					if err := json.Unmarshal([]byte(toolCall.Function.Arguments), &extractedParams); err != nil {
						return nil, fmt.Errorf("failed to parse function call arguments (%s) from LLM: %w", toolCall.Function.Arguments, err)
					}
					if len(extractedParams.Filepaths) == 0 {
						// LLM called the tool without any files to read.
						// Send feedback, no need to run the tool.
						params.Messages.Value = append(
							params.Messages.Value,
							openai.ToolMessage(toolCall.ID, ToolReadFilesNoFilesSpecifiedPrompt),
						)
						continue
					}

					ai.L.Debug(
						"Tool info",
						map[string]string{
							"tool":      toolCall.Function.Name,
							"filepaths": strings.Join(extractedParams.Filepaths, "\n"),
						},
					)

					projectFiles, err := req.ProjectDirectory.ReadFiles(extractedParams.Filepaths)
					if err != nil {
						// If no such file or directory was found, the LLM probably hallucinated and gave an incorrect filepath.
						// Send feedback to it.
						if errors.Is(err, fs.ErrNotExist) {
							data := map[string]string{
								"Filepath": "",
							}
							if pathErr, ok := err.(*fs.PathError); ok {
								data["Filepath"] = pathErr.Path
							}
							fileNotFoundPrompt, _ := promptcreator.ConstructPrompt(RequestedFileNotFoundPrompt, data)

							ai.L.Debug(
								"Filepath requested by LLM does not exist, sending feedback to it.",
								map[string]string{
									"filepath":        data["Filepath"],
									"response_to_llm": fileNotFoundPrompt,
								},
							)

							params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, fileNotFoundPrompt))
							continue
						}

						return nil, fmt.Errorf("failed to read file(s) from the project requested by LLM: %w", err)
					}

					responsePrompt := ""
					for path, content := range projectFiles {
						var filePrompt string

						if len(strings.TrimSpace(content)) == 0 {
							filePrompt = fmt.Sprintf("%s\n[File is empty]\n\n", path)
						} else {
							data := map[string]string{
								"TripleBackticks": "```",
								"Filepath":        path,
								"Content":         content,
							}
							filePrompt, _ = promptcreator.ConstructPrompt(ToolReadFilesResponseSingleFilePrompt, data)
						}

						responsePrompt += filePrompt
					}

					ai.L.Debug(
						fmt.Sprintf("Tool %s response: Sending back the files requested by LLM", ToolReadFiles),
						nil,
					)

					params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, responsePrompt))
					continue
				}

				if toolCall.Function.Name == ToolDeveloperFeedback {
					var extractedParams struct {
						Feedback string `json:"feedback"`
					}
					if err := json.Unmarshal([]byte(toolCall.Function.Arguments), &extractedParams); err != nil {
						return nil, fmt.Errorf("failed to parse %s function call arguments (%s) from LLM: %w", ToolDeveloperFeedback, toolCall.Function.Arguments, err)
					}

					ai.L.Debug(
						fmt.Sprintf("Received feedback for Developer from LLM"),
						map[string]string{
							"feedback": extractedParams.Feedback,
						},
					)

					params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, extractedParams.Feedback))
				}
			}
		}
	}

	return nil, fmt.Errorf("Maximum number of LLM calls reached")
}

func (ai *AIService) constructOptimizeSystemInstructions(req *OptimizeRequest) (string, error) {
	data := map[string]string{
		"Backtick":              "`",
		"TripleBackticks":       "```",
		"ToolReadFiles":         ToolReadFiles,
		"ToolDeveloperFeedback": ToolDeveloperFeedback,
	}

	multistageBuildsPrompt := ""
	if req.DockerfileStageCount == 1 {
		// Only add instructions for multistage builds if the Dockerfile is single-stage
		multistageBuildsPrompt, _ = promptcreator.ConstructPrompt(RuleMultistageBuildsPrompt, data)
	}

	data["RuleMultistageBuilds"] = multistageBuildsPrompt
	return promptcreator.ConstructPrompt(OptimizeRequestSystemPrompt, data)
}

func (ai *AIService) constructOptimizeUserQuery(req *OptimizeRequest) (string, error) {
	data := map[string]string{
		"Backtick":        "`",
		"TripleBackticks": "```",
		"DirTree":         req.ProjectDirectory.DirTree(),
		"Dockerfile":      req.Dockerfile,
		"PackageJSON":     req.PackageJSON,
	}
	return promptcreator.ConstructPrompt(OptimizeRequestUserPrompt, data)
}
