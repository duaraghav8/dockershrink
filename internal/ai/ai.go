package ai

import (
	"github.com/duaraghav8/dockershrink/internal/log"
	"github.com/openai/openai-go"
)

const MaxLLMCalls = 5

type AIService struct {
	L      *log.Logger
	client *openai.Client
	model	 string
}

func NewAIService(logger *log.Logger, client *openai.Client, model string) *AIService {
	return &AIService{
		L:      logger,
		client: client,
		model:  model,
	}
}
