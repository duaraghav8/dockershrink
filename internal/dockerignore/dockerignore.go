package dockerignore

import (
	"strings"
)

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
	for _, entry := range originalEntries {
		originalEntriesSet[strings.TrimSpace(entry)] = struct{}{}
	}

	toBeAdded := []string{}
	for _, entry := range entries {
		if _, exists := originalEntriesSet[entry]; !exists {
			toBeAdded = append(toBeAdded, entry)
		}
	}

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
