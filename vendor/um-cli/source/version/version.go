package version

import (
	"fmt"
	"runtime"
	"runtime/debug"
)

var (
	AppVersion = "dev"
	GitCommit  = "unknown"
	BuildDate  = "unknown"
)

func init() {
	if info, ok := debug.ReadBuildInfo(); ok {
		if info.Main.Version != "" && info.Main.Version != "(devel)" {
			AppVersion = info.Main.Version
		}

		for _, setting := range info.Settings {
			if setting.Key == "vcs.revision" {
				GitCommit = setting.Value[:8]
			}
			if setting.Key == "vcs.time" {
				BuildDate = setting.Value
			}
		}
	}
}

func GetVersion() string {
	return AppVersion
}

func GetFullVersion() string {
	return fmt.Sprintf("%s (%s, %s/%s, commit %s)",
		AppVersion,
		runtime.Version(),
		runtime.GOOS,
		runtime.GOARCH,
		GitCommit,
	)
}

func GetBuildInfo() map[string]string {
	return map[string]string{
		"version":    AppVersion,
		"git_commit": GitCommit,
		"build_date": BuildDate,
		"go_version": runtime.Version(),
		"platform":   fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH),
	}
}