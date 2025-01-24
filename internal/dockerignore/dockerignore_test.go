package dockerignore

import (
	"strings"
	"testing"
)

func TestDockerignore_AddIfNotPresent(t *testing.T) {
	initial := "node_modules\n.env"
	d := NewDockerignore(initial)
	toAdd := []string{"dist", "node_modules", "coverage"}

	added := d.AddIfNotPresent(toAdd)
	if len(added) != 2 || added[0] != "dist" || added[1] != "coverage" {
		t.Errorf("expected added entries ['dist','coverage'], got %v", added)
	}
	if !strings.Contains(d.Raw(), "dist") || !strings.Contains(d.Raw(), "coverage") {
		t.Errorf("expected Dockerignore to include 'dist' and 'coverage'")
	}

	added = d.AddIfNotPresent(toAdd)
	if len(added) != 0 {
		t.Errorf("expected no more added entries, got %v", added)
	}
}

func TestDockerignore_AddIfNotPresent_Empty(t *testing.T) {
	d := NewDockerignore("")
	toAdd := []string{"dist", "coverage"}

	added := d.AddIfNotPresent(toAdd)
	if len(added) != 2 || added[0] != "dist" || added[1] != "coverage" {
		t.Errorf("expected added entries ['dist','coverage'], got %v", added)
	}

	// Check the raw content has no leading newline
	if d.Raw() != "dist\ncoverage" {
		t.Errorf("expected 'dist\\ncoverage', got %q", d.Raw())
	}
}

func TestDockerignore_AddIfNotPresent_TrailingSlashHandling(t *testing.T) {
	// dockerignore already contains "node_modules"
	d := NewDockerignore("node_modules/\nbuild\n.git/\n.github")
	toAdd := []string{"node_modules", ".git", ".github"}

	// Attempt to add "node_modules/"
	added := d.AddIfNotPresent(toAdd)
	if len(added) != 0 {
		t.Errorf("expected 0 entries added, got %v", added)
	}

	// Ensure the content wasn't duplicated
	if strings.Count(d.Raw(), "node_modules") != 1 {
		t.Errorf("expected only one 'node_modules' entry, got %q", d.Raw())
	}

	d = NewDockerignore("node_modules/\nbuild\n.git/\n\n")
	added = d.AddIfNotPresent(toAdd)

	if len(added) != 1 {
		t.Errorf("expected only 1 entry added, got %v", added)
	}
	if added[0] != ".github" {
		t.Errorf("expected added entry '.github', got %q", added[0])
	}
}
