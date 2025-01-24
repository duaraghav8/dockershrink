package project

import (
	"testing"

	"github.com/duaraghav8/dockershrink/internal/dockerfile"
)

func TestIsAlpineOrSlim(t *testing.T) {
	tests := []struct {
		image    string
		expected bool
	}{
		{"node:18-alpine", true},
		{"node:18-slim", true},
		{"node:current-bullseye-slim", true},
		{"node:current-bullseye", false},
		{"node:lts-bookworm-slim", true},
		{"node:lts-bookworm", false},
		{"node:18", false},
		{"ubuntu:20.04", false},
		{"python:3.11-slim", true},
	}

	for _, tt := range tests {
		t.Run(tt.image, func(t *testing.T) {
			got := isAlpineOrSlim(dockerfile.NewImage(tt.image))
			if got != tt.expected {
				t.Errorf("isAlpineOrSlim(%q) = %v; want %v", tt.image, got, tt.expected)
			}
		})
	}
}

func TestGetNodeAlpineEquivalentTagForImage(t *testing.T) {
	tests := []struct {
		image    string
		expected string
	}{
		{"node:18", "18-alpine"},
		{"node:16.13", "16.13-alpine"},
		{"node:lts", "lts-alpine"},
		{"node:current-bullseye", "current-bullseye-slim"},
		{"node:lts-bookworm", "lts-bookworm-slim"},
		{"ubuntu:20.04", ""},            // not a node image
		{"python:3.11", ""},             // not a node image
		{"node:18-alpine", "18-alpine"}, // already alpine
	}

	for _, tt := range tests {
		t.Run(tt.image, func(t *testing.T) {
			got := getNodeAlpineEquivalentTagForImage(dockerfile.NewImage(tt.image))
			if got != tt.expected {
				t.Errorf("getNodeAlpineEquivalentTagForImage(%q) = %q; want %q", tt.image, got, tt.expected)
			}
		})
	}
}
