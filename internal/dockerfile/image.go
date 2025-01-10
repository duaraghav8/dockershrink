package dockerfile

import "strings"

const (
	DefaultTag = "latest"
	NameTagSep = ":"
)

type Image struct {
	name string
	tag  string
}

func NewImage(fullName string) *Image {
	parts := strings.Split(fullName, NameTagSep)
	if len(parts) == 1 {
		return &Image{name: parts[0], tag: DefaultTag}
	}
	return &Image{name: parts[0], tag: parts[1]}
}

// Name returns the name of the image.
// This is not the full name.
// For example, for the image "node:alpine", the name is "node".
func (i *Image) Name() string {
	return i.name
}

// Tag returns the tag of the image.
// For example, for the image "node:alpine", the tag is "alpine".
func (i *Image) Tag() string {
	return i.tag
}

// FullName returns the full name of the image.
// For example, for the image "node:alpine", the full name is "node:alpine".
func (i *Image) FullName() string {
	return i.name + NameTagSep + i.tag
}
