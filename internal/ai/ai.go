package ai

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/openai/openai-go"
)

const (
	OpenAIPreferredModel = openai.ChatModelGPT4o2024_11_20
	MaxLLMCalls          = 10
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
	systemInstructions := ""
	userQuery := ""

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
	availableTools := []openai.ChatCompletionToolParam{
		{
			Type: openai.F(openai.ChatCompletionToolTypeFunction),
			Function: openai.F(openai.FunctionDefinitionParam{
				Name:        openai.String("read_files"),
				Description: openai.String("Read the contents of specific files inside the project"),
				Parameters: openai.F(openai.FunctionParameters{
					"type": "object",
					"properties": map[string]interface{}{
						"filepaths": map[string]interface{}{
							"type":        "array",
							"items":       "string",
							"description": "List of files to read. Each item in the array is a file path relative to the project root directory.",
						},
					},
					"required": []string{"filepaths"},
				}),
			}),
		},
	}
	// TODO: Enable "get_documentation" tool call

	for i := 0; i < MaxLLMCalls; i++ {
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
		response, err := ai.client.Chat.Completions.New(context.Background(), params)
		if err != nil {
			return nil, fmt.Errorf("failed to get chat completion: %w", err)
		}

		toolCalls := response.Choices[0].Message.ToolCalls
		if len(toolCalls) == 0 {
			// no tool calls, the optimized Dockerfile has been returned by the LLM
			optimizeResponse := OptimizeResponse{}
			err = json.Unmarshal([]byte(response.Choices[0].Message.Content), &optimizeResponse)
			if err != nil {
				return nil, fmt.Errorf("failed to parse final response from LLM: %w", err)
			}
			return &optimizeResponse, nil
		} else {
			// add the tool call message back to the ongoing conversation with LLM
			params.Messages.Value = append(params.Messages.Value, response.Choices[0].Message)

			for _, toolCall := range toolCalls {
				if toolCall.Function.Name == "read_files" {
					var extractedParams struct {
						FilePaths []string `json:"filepaths"`
					}
					if err := json.Unmarshal([]byte(toolCall.Function.Arguments), &extractedParams); err != nil {
						return nil, fmt.Errorf("failed to parse function call arguments (%s) from LLM: %w", toolCall.Function.Arguments, err)
					}

					projectFiles, err := req.ProjectDirectory.ReadFiles(extractedParams.FilePaths)
					if err != nil {
						return nil, fmt.Errorf("failed to read files from the project requested by LLM: %w", err)
					}
					projectFilesJSON, err := json.Marshal(projectFiles)
					if err != nil {
						return nil, fmt.Errorf("failed to convert project files into JSON object: %w", err)
					}
					params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, string(projectFilesJSON)))
				}
			}
		}
	}

	return nil, fmt.Errorf("maximum number of LLM calls reached")
}
