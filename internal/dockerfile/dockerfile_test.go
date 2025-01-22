package dockerfile

import (
	"strings"
	"testing"

	"github.com/moby/buildkit/frontend/dockerfile/parser"
)

func TestValidate(t *testing.T) {
	t.Run("Valid Dockerfile", func(t *testing.T) {
		validDockerfile := `FROM node:18-alpine
RUN echo "Hello World"`
		ok, err := Validate(validDockerfile)
		if err != nil {
			t.Fatalf("expected valid Dockerfile, got error: %v", err)
		}
		if !ok {
			t.Fatal("expected Validate to return true for valid Dockerfile")
		}
	})

	// TODO: enable this test once Validate() can detect dyntactical errors in Dockerfile
	/*
			t.Run("Syntax Error", func(t *testing.T) {
				syntaxErrorDockerfile := `"""
		FROM node:18-alpine
		RUN echo "Hello World"
		"""
		Some random gibberish text`
				ok, err := Validate(syntaxErrorDockerfile)
				if err == nil {
					t.Fatal("expected an error for Dockerfile with syntax error, got nil")
				}
				if ok {
					t.Fatal("expected Validate to return false for Dockerfile with syntax error")
				}
			})
	*/
}

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
