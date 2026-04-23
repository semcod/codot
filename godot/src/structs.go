
// structs.go - generated from JSON
package main

type GeneratedViewBundle struct {
	Bundle      string                `json:"bundle"`
	Kind        string                `json:"kind"`
	Version     string                `json:"version"`
	Description string                `json:"description"`
	Sources     []GeneratedViewSource `json:"sources"`
	Template    GeneratedTemplate     `json:"template"`
	Output      GeneratedViewOutput   `json:"output"`
}

type GeneratedViewSource struct {
	Name       string   `json:"name"`
	URI        string   `json:"uri"`
	RefreshSec int      `json:"refresh_sec,omitempty"`
	Type       string   `json:"type"`
	DependsOn  []string `json:"depends_on,omitempty"`
}

type GeneratedTemplate struct {
	Engine    string `json:"engine"`
	SourceURI string `json:"source_uri"`
}

type GeneratedViewOutput struct {
	Format  string `json:"format"`
	Runtime *struct {
		Port int    `json:"port,omitempty"`
		Lang string `json:"lang,omitempty"`
	} `json:"runtime,omitempty"`
}
