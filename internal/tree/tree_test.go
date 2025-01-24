package tree

import "testing"

func TestContains(t *testing.T) {
	tests := []struct {
		name     string
		slice    []string
		item     string
		expected bool
	}{
		{
			name:     "Item present in slice",
			slice:    []string{"apple", "banana", "cherry"},
			item:     "banana",
			expected: true,
		},
		{
			name:     "Item not present in slice",
			slice:    []string{"apple", "banana", "cherry"},
			item:     "mango",
			expected: false,
		},
		{
			name:     "Empty slice",
			slice:    []string{},
			item:     "anything",
			expected: false,
		},
		{
			name:     "Single element slice with match",
			slice:    []string{"unique"},
			item:     "unique",
			expected: true,
		},
		{
			name:     "Single element slice without match",
			slice:    []string{"unique"},
			item:     "other",
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := contains(tt.slice, tt.item)
			if got != tt.expected {
				t.Errorf("contains(%v, %q) = %v; want %v", tt.slice, tt.item, got, tt.expected)
			}
		})
	}
}
