package dockerfile

import (
	"strings"
	"testing"

	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

func TestDockerfile_GetStageCount(t *testing.T) {
	dockerfileContent := `FROM node:18-alpine
FROM python:3.11
`
	parsed, err := parser.Parse(strings.NewReader(dockerfileContent))
	if err != nil {
		t.Fatalf("error parsing dockerfile content: %v", err)
	}
	df := &Dockerfile{
		code: dockerfileContent,
		ast:  parsed.AST,
	}

	stageCount := df.GetStageCount()
	if stageCount != 2 {
		t.Fatalf("expected 2 stages, got %d", stageCount)
	}
}

func TestDockerfile_GetFinalStage(t *testing.T) {
	dockerfileContent := `FROM node:18-alpine
FROM python:3.11
`
	parsed, err := parser.Parse(strings.NewReader(dockerfileContent))
	if err != nil {
		t.Fatalf("error parsing dockerfile content: %v", err)
	}

	df := &Dockerfile{
		code: dockerfileContent,
		ast:  parsed.AST,
	}

	finalStage, err := df.GetFinalStage()
	if err != nil {
		t.Fatalf("GetFinalStage returned an error: %v", err)
	}

	if finalStage.BaseImage().FullName() != "python:3.11" {
		t.Errorf("expected final stage image 'python:3.11', got '%s'", finalStage.BaseImage().FullName())
	}
}

func TestDockerfile_SetStageBaseImage(t *testing.T) {
	dockerfileContent := `FROM node:18-alpine
FROM python:3.11
`
	parsed, err := parser.Parse(strings.NewReader(dockerfileContent))
	if err != nil {
		t.Fatalf("error parsing dockerfile content: %v", err)
	}

	df := &Dockerfile{
		code: dockerfileContent,
		ast:  parsed.AST,
	}

	finalStage, err := df.GetFinalStage()
	if err != nil {
		t.Fatalf("GetFinalStage returned an error: %v", err)
	}

	newImage := NewImage("alpine:latest")
	df.SetStageBaseImage(finalStage, newImage)

	if !strings.Contains(df.code, "alpine:latest") {
		t.Errorf("expected dockerfile to contain 'alpine:latest'")
	}
	// Re-verify final stage's base image
	updatedStage, err := df.GetFinalStage()
	if err != nil {
		t.Fatalf("error calling GetFinalStage after update: %v", err)
	}
	if updatedStage.BaseImage().FullName() != "alpine:latest" {
		t.Errorf("expected updated final stage image 'alpine:latest', got '%s'", updatedStage.BaseImage().FullName())
	}
}
