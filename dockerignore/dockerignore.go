package dockerignore

type Dockerignore struct {
}

func NewDockerignore(content string) (*Dockerignore, error) {
	return &Dockerignore{}, nil
}

func (d *Dockerignore) Exists() bool {
	return false
}

func (d *Dockerignore) Create() error {
	return nil
}

func (d *Dockerignore) AddIfNotPresent(entries []string) []string {
	return []string{}
}

func (d *Dockerignore) Raw() string {
	return ""
}
