package dockerfile

type Image struct {
	name string
	tag  string
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
