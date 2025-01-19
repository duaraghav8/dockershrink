package ai

import "github.com/openai/openai-go"

// TODO: Add the "get_documentation" tool

const (
	ToolReadFiles         = "read_files"
	ToolDeveloperFeedback = "developer_feedback"
)

var availableTools = []openai.ChatCompletionToolParam{
	{
		Type: openai.F(openai.ChatCompletionToolTypeFunction),
		Function: openai.F(openai.FunctionDefinitionParam{
			Name:        openai.String(ToolReadFiles),
			Description: openai.String("Read the contents of specific files inside the project"),
			Parameters: openai.F(openai.FunctionParameters{
				"type": "object",
				"properties": map[string]interface{}{
					"filepaths": map[string]interface{}{
						"type":        "array",
						"items":       map[string]interface{}{"type": "string"},
						"description": "List of files to read. Each item in the array is a file path relative to the project root directory.",
					},
				},
				"required": []string{"filepaths"},
			}),
		}),
	},
	{
		Type: openai.F(openai.ChatCompletionToolTypeFunction),
		Function: openai.F(openai.FunctionDefinitionParam{
			Name:        openai.String(ToolDeveloperFeedback),
			Description: openai.String("Provide feedback to your developer about what can be improved"),
			Parameters: openai.F(openai.FunctionParameters{
				"type": "object",
				"properties": map[string]interface{}{
					"feedback": map[string]interface{}{
						"type":        "string",
						"description": "Feedback you want the developer to read",
					},
				},
				"required": []string{"feedback"},
			}),
		}),
	},
}
