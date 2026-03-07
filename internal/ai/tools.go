package ai

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"strings"
	"github.com/openai/openai-go"
)

// Token limit for file reading
const tokenLimit = 4000

// Handle read_files tool
func HandleReadFiles(toolCall openai.ChatCompletionMessageToolCall, req *GenerateRequest, params *openai.ChatCompletionNewParams) error {
	var extractedParams struct {
		Filepaths []string `json:"filepaths"`
	}
	if err := json.Unmarshal([]byte(toolCall.Function.Arguments), &extractedParams); err != nil {
		return fmt.Errorf("failed to parse function arguments: %w", err)
	}

	if len(extractedParams.Filepaths) == 0 {
		params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, ToolReadFilesNoFilesSpecifiedPrompt))
		return nil
	}

	projectFiles, err := req.ProjectDirectory.ReadFiles(extractedParams.Filepaths)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return SendFileNotFoundMessage(toolCall, err, params)
		}
		return fmt.Errorf("failed to read requested files: %w", err)
	}

	truncatedFiles := DistributeTokensForFiles(projectFiles)
	var responsePrompt strings.Builder

	for path, content := range truncatedFiles {
		responsePrompt.WriteString(fmt.Sprintf("```%s\n%s\n```\n", path, content))
	}

	params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, responsePrompt.String()))
	return nil
}

// Handle developer_feedback tool
func HandleDeveloperFeedback(toolCall openai.ChatCompletionMessageToolCall, params *openai.ChatCompletionNewParams) error {
	var extractedParams struct {
		Feedback string `json:"feedback"`
	}
	if err := json.Unmarshal([]byte(toolCall.Function.Arguments), &extractedParams); err != nil {
		return fmt.Errorf("failed to parse developer feedback arguments: %w", err)
	}

	params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, extractedParams.Feedback))
	return nil
}
