package sniff

import "mime"

// ref: https://mimesniff.spec.whatwg.org
var imageMIMEs = map[string]Sniffer{
	"image/jpeg": prefixSniffer{0xFF, 0xD8, 0xFF},
	"image/png":  prefixSniffer{0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n'},
	"image/bmp":  prefixSniffer("BM"),
	"image/webp": prefixSniffer("RIFF"),
	"image/gif":  prefixSniffer("GIF8"),
}

// preferredExt maps MIME types to a preferred file extension,
// overriding the first result from mime.ExtensionsByType when needed.
var preferredExt = map[string]string{
	"image/jpeg": ".jpg", // mime package may return ".jpeg" first
}

// ImageMIME sniffs the well-known image types, and returns its MIME.
func ImageMIME(header []byte) (string, bool) {
	for mimeType, sniffer := range imageMIMEs {
		if sniffer.Sniff(header) {
			return mimeType, true
		}
	}
	return "", false
}

// ImageExtension is equivalent to ImageMIME, but returns a file extension.
// It uses mime.ExtensionsByType from the standard library, with a fixed
// preference table for types that have multiple valid extensions (e.g. JPEG).
func ImageExtension(header []byte) (string, bool) {
	mimeType, ok := ImageMIME(header)
	if !ok {
		return "", false
	}

	// Check preferred mapping first
	if ext, ok := preferredExt[mimeType]; ok {
		return ext, true
	}

	// Fall back to standard library
	exts, err := mime.ExtensionsByType(mimeType)
	if err != nil || len(exts) == 0 {
		return "", false
	}
	return exts[0], true
}
