package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"gopkg.in/yaml.v3"
)

type Config struct {
	OutputDir      string `yaml:"output_dir"`
	SkipNoop       bool   `yaml:"skip_noop"`
	UpdateMetadata bool   `yaml:"update_metadata"`
	Overwrite      bool   `yaml:"overwrite"`
	Verbose        bool   `yaml:"verbose"`
	RemoveSource   bool   `yaml:"remove_source"`
	QmcMmkv        string `yaml:"qmc_mmkv"`
	QmcMmkvKey     string `yaml:"qmc_mmkv_key"`
	KggDb          string `yaml:"kgg_db"`
	Concurrency    int    `yaml:"concurrency"`
	Progress       bool   `yaml:"progress"`
	NameTemplate   string `yaml:"name_template"`
}

func DefaultConfig() *Config {
	return &Config{
		SkipNoop:    true,
		Concurrency: 1,
		Progress:    true,
	}
}

func LoadConfig() (*Config, error) {
	paths, err := getConfigPaths()
	if err != nil {
		return DefaultConfig(), nil
	}

	cfg := DefaultConfig()

	for _, path := range paths {
		if _, err := os.Stat(path); err != nil {
			continue
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("read config %s: %w", path, err)
		}

		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("parse config %s: %w", path, err)
		}

		break
	}

	return cfg, nil
}

func getConfigPaths() ([]string, error) {
	var paths []string

	paths = append(paths, ".um.yaml")
	paths = append(paths, "um.yaml")

	home, err := os.UserHomeDir()
	if err != nil {
		return paths, nil
	}

	paths = append(paths, filepath.Join(home, ".um.yaml"))
	paths = append(paths, filepath.Join(home, ".config", "um", "config.yaml"))

	if runtime.GOOS == "windows" {
		appData := os.Getenv("APPDATA")
		if appData != "" {
			paths = append(paths, filepath.Join(appData, "um", "config.yaml"))
		}
	}

	return paths, nil
}