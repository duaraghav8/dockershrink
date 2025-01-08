package project

import (
	"strings"

	"github.com/duaraghav8/dockershrink/internal/dockerfile"
)

func getNodeAlpineEquivalentTagForImage(image *dockerfile.Image) string {
	tag := image.Tag()
	if strings.Contains(tag, "alpine") {
		return tag
	}

	parts := strings.Split(tag, ".")
	if len(parts) > 0 {
		return parts[0] + "-alpine"
	}

	return "alpine"
}
