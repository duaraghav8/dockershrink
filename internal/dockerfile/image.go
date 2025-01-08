package dockerfile

import "strings"

type Image struct {
	name string
	tag  string
}

func NewImage(fullName string) *Image {
	parts := strings.Split(fullName, ":")
	if len(parts) == 1 {
		return &Image{name: parts[0], tag: "latest"}
	}
	return &Image{name: parts[0], tag: parts[1]}
}

func (i *Image) Name() string {
	return i.name
}

func (i *Image) Tag() string {
	return i.tag
}

// Equals checks if two images are the same
func (i *Image) Equals(other *Image) bool {
	return i.Name() == other.Name() && i.Tag() == other.Tag()
}

func (i *Image) IsAlpineOrSlim() bool {
	return true
}

func (i *Image) FullName() string {
	return i.name + ":" + i.tag
}
