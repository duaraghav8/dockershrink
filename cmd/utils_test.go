package cmd

import (
    "os"
    "testing"
)

func TestResolveAPIKey_PrefersFlag(t *testing.T) {
    apiKey = "flag-key"
    os.Setenv("DOCKERSHRINK_API_KEY", "env-key")
    defer os.Unsetenv("DOCKERSHRINK_API_KEY")

    got := resolveAPIKey()
    if got != "flag-key" {
        t.Errorf("expected 'flag-key', got %q", got)
    }
    apiKey = ""
}

func TestResolveAPIKey_PrefersEnv(t *testing.T) {
    apiKey = ""
    os.Setenv("DOCKERSHRINK_API_KEY", "env-key")
    defer os.Unsetenv("DOCKERSHRINK_API_KEY")

    got := resolveAPIKey()
    if got != "env-key" {
        t.Errorf("expected 'env-key', got %q", got)
    }
}

func TestResolveBaseURL_OllamaDefault(t *testing.T) {
    apiKey = "ollama"
    baseUrl = ""
    os.Setenv("DOCKERSHRINK_BASE_URL", "")
    defer os.Unsetenv("DOCKERSHRINK_BASE_URL")

    got := resolveBaseURL()
    want := "http://localhost:11434/v1/"
    if got != want {
        t.Errorf("expected %q, got %q", want, got)
    }
}