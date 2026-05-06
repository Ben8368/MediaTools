package report

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"time"
)

type ProcessingReport struct {
	Metadata   ReportMetadata `json:"metadata"`
	Statistics Statistics     `json:"statistics"`
	Files      []FileReport   `json:"files"`
}

type ReportMetadata struct {
	Timestamp   time.Time `json:"timestamp"`
	Version     string    `json:"version"`
	Platform    string    `json:"platform"`
	Concurrency int       `json:"concurrency"`
}

type Statistics struct {
	Total      int     `json:"total"`
	Success    int     `json:"success"`
	Failed     int     `json:"failed"`
	Skipped    int     `json:"skipped"`
	TotalBytes int64   `json:"total_bytes"`
	DurationMs int64   `json:"duration_ms"`
	AvgSpeed   float64 `json:"avg_speed_mb_per_sec"`
}

type FileReport struct {
	Source      string `json:"source"`
	Destination string `json:"destination,omitempty"`
	Status      string `json:"status"`
	Error       string `json:"error,omitempty"`
	DurationMs  int64  `json:"duration_ms"`
	BytesIn     int64  `json:"bytes_in,omitempty"`
	BytesOut    int64  `json:"bytes_out,omitempty"`
}

func NewReport(version string, concurrency int) *ProcessingReport {
	return &ProcessingReport{
		Metadata: ReportMetadata{
			Timestamp:   time.Now(),
			Version:     version,
			Platform:    fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH),
			Concurrency: concurrency,
		},
		Statistics: Statistics{},
		Files:      []FileReport{},
	}
}

func (r *ProcessingReport) AddSuccess(source, dest string, durationMs int64, bytesIn, bytesOut int64) {
	r.Files = append(r.Files, FileReport{
		Source:      source,
		Destination: dest,
		Status:      "success",
		DurationMs:  durationMs,
		BytesIn:     bytesIn,
		BytesOut:    bytesOut,
	})
	r.Statistics.Success++
	r.Statistics.Total++
	r.Statistics.TotalBytes += bytesIn
	r.Statistics.DurationMs += durationMs
}

func (r *ProcessingReport) AddFailed(source string, err string) {
	r.Files = append(r.Files, FileReport{
		Source: source,
		Status: "failed",
		Error:  err,
	})
	r.Statistics.Failed++
	r.Statistics.Total++
}

func (r *ProcessingReport) AddSkipped(source string) {
	r.Files = append(r.Files, FileReport{
		Source: source,
		Status: "skipped",
	})
	r.Statistics.Skipped++
	r.Statistics.Total++
}

func (r *ProcessingReport) Finalize() {
	if r.Statistics.DurationMs > 0 {
		totalMB := float64(r.Statistics.TotalBytes) / (1024 * 1024)
		totalSec := float64(r.Statistics.DurationMs) / 1000
		r.Statistics.AvgSpeed = totalMB / totalSec
	}
}

func (r *ProcessingReport) SaveJSON(path string) error {
	r.Finalize()

	data, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal report: %w", err)
	}

	return os.WriteFile(path, data, 0644)
}

func (r *ProcessingReport) SaveCSV(path string) error {
	r.Finalize()

	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create csv: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)

	headers := []string{"source", "destination", "status", "error", "duration_ms", "bytes_in", "bytes_out"}
	writer.Write(headers)

	for _, f := range r.Files {
		row := []string{
			f.Source,
			f.Destination,
			f.Status,
			f.Error,
			fmt.Sprintf("%d", f.DurationMs),
			fmt.Sprintf("%d", f.BytesIn),
			fmt.Sprintf("%d", f.BytesOut),
		}
		writer.Write(row)
	}

	writer.Flush()
	return writer.Error()
}