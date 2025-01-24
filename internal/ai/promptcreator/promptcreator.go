package promptcreator

import (
	"bytes"
	"fmt"
	"text/template"
)

// ConstructPrompt parses the given templateText, then executes it using data from
// the provided map[string]string.
// If the template references a key not in data, it returns an error.
func ConstructPrompt(templateText string, data map[string]string) (string, error) {
	tmpl, err := template.New("prompt").
		Option("missingkey=error").
		Parse(templateText)
	if err != nil {
		return "", fmt.Errorf("failed to parse template: %w", err)
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, data); err != nil {
		return "", fmt.Errorf("failed to execute template: %w", err)
	}

	return buf.String(), nil
}
