package ffmpeg

import (
	"context"
	"os/exec"
	"strings"
)

type ffmpegBuilder struct {
	binary  string          // ffmpeg binary path
	flags   []string        // global flags/options, ordered
	inputs  []*inputBuilder // input options
	outputs []*outputBuilder // output options
}

func newFFmpegBuilder() *ffmpegBuilder {
	return &ffmpegBuilder{binary: "ffmpeg"}
}

func (b *ffmpegBuilder) AddInput(src *inputBuilder) {
	b.inputs = append(b.inputs, src)
}

func (b *ffmpegBuilder) AddOutput(dst *outputBuilder) {
	b.outputs = append(b.outputs, dst)
}

func (b *ffmpegBuilder) SetBinary(bin string) {
	b.binary = bin
}

// SetFlag appends a boolean flag (e.g. "-y") in order.
func (b *ffmpegBuilder) SetFlag(flag string) {
	b.flags = append(b.flags, "-"+flag)
}

// SetOption appends a key-value option (e.g. "-loglevel quiet") in order.
func (b *ffmpegBuilder) SetOption(name, value string) {
	b.flags = append(b.flags, "-"+name, value)
}

func (b *ffmpegBuilder) Args() (args []string) {
	args = append(args, b.flags...)

	for _, input := range b.inputs {
		args = append(args, input.Args()...)
	}
	for _, output := range b.outputs {
		args = append(args, output.Args()...)
	}

	return
}

func (b *ffmpegBuilder) Command(ctx context.Context) *exec.Cmd {
	bin := "ffmpeg"
	if b.binary != "" {
		bin = b.binary
	}

	return exec.CommandContext(ctx, bin, b.Args()...)
}

// inputBuilder is the builder for ffmpeg input options
type inputBuilder struct {
	path    string
	options []kv // ordered key-value pairs
}

func newInputBuilder(path string) *inputBuilder {
	return &inputBuilder{path: path}
}

func (b *inputBuilder) AddOption(name, value string) {
	b.options = append(b.options, kv{name, value})
}

func (b *inputBuilder) Args() (args []string) {
	for _, o := range b.options {
		args = append(args, "-"+o.k, o.v)
	}
	return append(args, "-i", b.path)
}

// outputBuilder is the builder for ffmpeg output options
type outputBuilder struct {
	path    string
	options []kv // ordered key-value pairs
}

func newOutputBuilder(path string) *outputBuilder {
	return &outputBuilder{path: path}
}

func (b *outputBuilder) AddOption(name, value string) {
	b.options = append(b.options, kv{name, value})
}

func (b *outputBuilder) Args() (args []string) {
	for _, o := range b.options {
		args = append(args, "-"+o.k, o.v)
	}
	return append(args, b.path)
}

// AddMetadata is the shortcut for adding "metadata" option
func (b *outputBuilder) AddMetadata(stream, key, value string) {
	optVal := strings.TrimSpace(key) + "=" + strings.TrimSpace(value)

	if stream != "" {
		b.AddOption("metadata:"+stream, optVal)
	} else {
		b.AddOption("metadata", optVal)
	}
}

// kv is an ordered key-value pair for ffmpeg options.
type kv struct {
	k, v string
}
