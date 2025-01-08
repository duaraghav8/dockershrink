package packagejson

import (
	"encoding/json"
	"errors"
)

type PackageJSON struct {
	rawData    map[string]interface{}
	rawDataStr string
}

func NewPackageJSON(content string) (*PackageJSON, error) {
	var data map[string]interface{}
	err := json.Unmarshal([]byte(content), &data)
	if err != nil {
		return nil, err
	}
	return &PackageJSON{rawData: data, rawDataStr: content}, nil
}

func (p *PackageJSON) GetScript(name string) (string, error) {
	scripts, ok := p.rawData["scripts"].(map[string]interface{})
	if !ok {
		return "", errors.New("scripts not found in package.json")
	}
	script, ok := scripts[name].(string)
	if !ok {
		return "", nil
	}
	return script, nil
}

func (p *PackageJSON) Raw() map[string]interface{} {
	return p.rawData
}

func (p *PackageJSON) String() string {
	return p.rawDataStr
}
