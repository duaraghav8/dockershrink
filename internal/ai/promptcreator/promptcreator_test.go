package promptcreator

import (
	"testing"
)

func TestConstructPrompt(t *testing.T) {
	templateText := `
Hello, {{ .name }}!
We see you're from {{ .city }}.
`
	data := map[string]string{
		"name": "Alice",
		"city": "Wonderland",
	}

	result, err := ConstructPrompt(templateText, data)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	expected := `
Hello, Alice!
We see you're from Wonderland.
`
	if result != expected {
		t.Errorf("got %q, want %q", result, expected)
	}
}

func TestMissingKey(t *testing.T) {
	// This template references .name and .age, but we'll only provide .name
	templateText := `
Hello, {{ .name }}!
You are {{ .age }} years old.
`
	data := map[string]string{
		"name": "Bob",
	}

	_, err := ConstructPrompt(templateText, data)
	if err == nil {
		t.Fatalf("expected an error for missing key 'age', but got none")
	}
}
