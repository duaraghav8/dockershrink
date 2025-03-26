package ai

import (
	"fmt"
	"io/fs"
	"strings"
	"github.com/openai/openai-go"
)

// Handle file not found scenario
func SendFileNotFoundMessage(toolCall openai.ChatCompletionMessageToolCall, err error, params *openai.ChatCompletionNewParams) error {
	filepath := ""
	if pathErr, ok := err.(*fs.PathError); ok {
		filepath = pathErr.Path
	}

	message := fmt.Sprintf("Requested file not found: %s", filepath)
	params.Messages.Value = append(params.Messages.Value, openai.ToolMessage(toolCall.ID, message))
	return nil
}

// DistributeTokens evenly distributes a token limit across multiple string variables.
func DistributeTokens(files ...*string) {
	if tokenLimit <= 0 || len(files) == 0 {
		return
	}

	tokensPerFile := tokenLimit / len(files)

	for _, content := range files {
		if content != nil {
			*content = truncateToLimit(*content, tokensPerFile)
		}
	}
}

// DistributeTokensForFiles applies a token limit across a map of file paths and content.
func DistributeTokensForFiles(files map[string]string) map[string]string {
	if tokenLimit <= 0 || len(files) == 0 {
		return files
	}

	tokensPerFile := tokenLimit / len(files)
	truncatedFiles := make(map[string]string)

	for path, content := range files {
		truncatedFiles[path] = truncateToLimit(content, tokensPerFile)
	}

	return truncatedFiles
}

// truncateToLimit trims content to fit within the token limit.
func truncateToLimit(text string, tokenLimit int) string {
	words := strings.Fields(text)
	if len(words) > tokenLimit {
		return strings.Join(words[:tokenLimit], " ") + "..." // Indicate truncation
	}
	return text
}

// CountTokens estimates the number of tokens in a string.
func CountTokens(text string) int {
	return len(strings.Fields(text)) // Simple word-based token estimation
}