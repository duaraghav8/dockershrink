package dockerignore

import (
	"strings"
)

// normalizeEntry removes leading/trailing whitespace and any trailing slash
func normalizeEntry(e string) string {
	norm := strings.TrimSpace(e)
	return strings.TrimSuffix(norm, "/")
}

type Dockerignore struct {
	rawData string
}

func NewDockerignore(content string) *Dockerignore {
	return &Dockerignore{rawData: content}
}

func (d *Dockerignore) Raw() string {
	return d.rawData
}

// AddIfNotPresent adds the given entries to the .dockerignore file if they are not already present in it.
// It returns the entries that were added.
func (d *Dockerignore) AddIfNotPresent(entries []string) []string {
	originalEntries := strings.Split(d.rawData, "\n")
	originalEntriesSet := make(map[string]struct{})

	// create the set of original entries
	for _, entry := range originalEntries {
		n := normalizeEntry(entry)
		if n == "" {
			continue
		}
		originalEntriesSet[n] = struct{}{}
	}

	// create a list of entries to be added
	toBeAdded := []string{}
	for _, entry := range entries {
		n := normalizeEntry(entry)
		if n == "" {
			continue
		}
		if _, exists := originalEntriesSet[n]; !exists {
			toBeAdded = append(toBeAdded, n)
			originalEntriesSet[n] = struct{}{}
		}
	}

	// join the new entries with the original and return the new dockerignore contents
	if len(toBeAdded) > 0 {
		joined := strings.Join(toBeAdded, "\n")
		trimmed := strings.TrimSpace(d.rawData)
		if trimmed == "" {
			// If dockerignore is empty, just join the new entries
			d.rawData = joined
		} else {
			// If not empty, add a newline before new entries
			d.rawData = trimmed + "\n" + joined
		}
	}

	return toBeAdded
}
