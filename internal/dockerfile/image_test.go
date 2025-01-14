package dockerfile

import (
	"testing"
)

func TestNewImage_SingleName(t *testing.T) {
	img := NewImage("node")
	if img.Name() != "node" {
		t.Errorf("expected name 'node', got %q", img.Name())
	}
	if img.Tag() != DefaultTag {
		t.Errorf("expected tag '%s', got %q", DefaultTag, img.Tag())
	}
	expectedFull := "node:" + DefaultTag
	if img.FullName() != expectedFull {
		t.Errorf("expected full name %q, got %q", expectedFull, img.FullName())
	}
}

func TestNewImage_NameAndTag(t *testing.T) {
	img := NewImage("node:alpine")
	if img.Name() != "node" {
		t.Errorf("expected name 'node', got %q", img.Name())
	}
	if img.Tag() != "alpine" {
		t.Errorf("expected tag 'alpine', got %q", img.Tag())
	}
	if img.FullName() != "node:alpine" {
		t.Errorf("expected full name 'node:alpine', got %q", img.FullName())
	}
}
