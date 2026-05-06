package naming

import (
	"bytes"
	"fmt"
	"strings"
	"text/template"
	"unicode"

	"git.um-react.app/um/cli/algo/common"
)

type NameTemplate struct {
	template *template.Template
}

func NewNameTemplate(pattern string) (*NameTemplate, error) {
	var tmpl *template.Template
	var err error

	if strings.Contains(pattern, "{{") {
		tmpl, err = template.New("filename").Parse(pattern)
		if err != nil {
			return nil, fmt.Errorf("parse template: %w", err)
		}
	} else {
		converted := convertSimplePattern(pattern)
		tmpl, err = template.New("filename").Parse(converted)
		if err != nil {
			return nil, fmt.Errorf("convert pattern: %w", err)
		}
	}

	return &NameTemplate{template: tmpl}, nil
}

func convertSimplePattern(pattern string) string {
	pattern = strings.ReplaceAll(pattern, "{artist}", "{{.Artist}}")
	pattern = strings.ReplaceAll(pattern, "{title}", "{{.Title}}")
	pattern = strings.ReplaceAll(pattern, "{album}", "{{.Album}}")
	pattern = strings.ReplaceAll(pattern, "{original}", "{{.Original}}")
	pattern = strings.ReplaceAll(pattern, "{ext}", "{{.Ext}}")
	return pattern
}

func (nt *NameTemplate) Execute(meta common.AudioMeta, original string, ext string) (string, error) {
	data := map[string]interface{}{
		"Artist":   getFirstArtist(meta),
		"Artists":  meta.GetArtists(),
		"Title":    meta.GetTitle(),
		"Album":    meta.GetAlbum(),
		"Original": strings.TrimSuffix(original, ext),
		"Ext":      ext,
	}

	var buf bytes.Buffer
	if err := nt.template.Execute(&buf, data); err != nil {
		return "", fmt.Errorf("execute template: %w", err)
	}

	result := buf.String()
	result = sanitizeFilename(result)

	return result, nil
}

func getFirstArtist(meta common.AudioMeta) string {
	artists := meta.GetArtists()
	if len(artists) > 0 {
		return artists[0]
	}
	return ""
}

func sanitizeFilename(name string) string {
	name = strings.Map(func(r rune) rune {
		switch r {
		case '\\', '/', ':', '*', '?', '"', '<', '>', '|':
			return '-'
		default:
			return r
		}
	}, name)

	name = strings.ReplaceAll(name, "--", "-")
	name = strings.TrimSpace(name)

	name = strings.Map(func(r rune) rune {
		if unicode.IsControl(r) {
			return -1
		}
		return r
	}, name)

	if len(name) > 200 {
		name = name[:200]
	}

	return name
}