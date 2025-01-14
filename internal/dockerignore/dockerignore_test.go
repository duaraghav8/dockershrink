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
