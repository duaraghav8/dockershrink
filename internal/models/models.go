package models

type OptimizationAction struct {
	Rule        string `json:"rule" jsonschema_description:"Name of the rule that was applied"`
	Filename    string `json:"filename" jsonschema_description:"Name of the file where the action was taken (most likely Dockerfile)"`
	Title       string `json:"title" jsonschema_description:"Title of the action taken"`
	Description string `json:"description" jsonschema_description:"Description of the action taken"`
	Line        int    `json:"line,omitempty" jsonschema_description:"(Field is Optional) Line number in the Dockerfile where the action was taken"`
}
