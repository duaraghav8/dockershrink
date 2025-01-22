package ai

import (
	"github.com/duaraghav8/dockershrink/internal/log"
	"github.com/openai/openai-go"
)

const (
	// 2024_08 version is performing better than 2024_11 for dockershrink
	OpenAIPreferredModel = openai.ChatModelGPT4o2024_08_06
	MaxLLMCalls          = 5
)

type AIService struct {
	L      *log.Logger
	client *openai.Client
}

func NewAIService(logger *log.Logger, client *openai.Client) *AIService {
	return &AIService{
		L:      logger,
		client: client,
	}
}
