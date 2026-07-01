// Package state tracks source-file hashes to support incremental compilation.
package state

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"time"
)

const defaultStateFile = ".compile-state.json"

// State persists hash and mtime info for source files.
type State struct {
	path    string
	Sources map[string]sourceEntry `json:"sources"`
}

type sourceEntry struct {
	Hash  string    `json:"hash"`
	Size  int64     `json:"size"`
	Mtime time.Time `json:"mtime"`
}

// Load reads a compile state from path (or returns an empty state if absent).
func Load(path string) (*State, error) {
	if path == "" {
		path = defaultStateFile
	}
	s := &State{path: path, Sources: make(map[string]sourceEntry)}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return s, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(data, s); err != nil {
		return s, nil
	}
	return s, nil
}

// Save writes the state to disk.
func (s *State) Save() error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.path, data, 0o644)
}

// SourceChanged returns true if the file at filePath has changed since last recorded.
func (s *State) SourceChanged(name, filePath string) bool {
	info, err := os.Stat(filePath)
	if err != nil {
		return true
	}
	prev, ok := s.Sources[name]
	if !ok {
		return true
	}
	if info.ModTime().Equal(prev.Mtime) && info.Size() == prev.Size {
		return false
	}
	hash, err := hashFile(filePath)
	if err != nil {
		return true
	}
	return hash != prev.Hash
}

// UpdateSource records the current hash and mtime for name at filePath.
func (s *State) UpdateSource(name, filePath string) error {
	info, err := os.Stat(filePath)
	if err != nil {
		return err
	}
	hash, err := hashFile(filePath)
	if err != nil {
		return err
	}
	s.Sources[name] = sourceEntry{
		Hash:  hash,
		Size:  info.Size(),
		Mtime: info.ModTime(),
	}
	return nil
}

func hashFile(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
