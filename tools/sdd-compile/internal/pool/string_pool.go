// Package pool implements string deduplication for the DSL compiler.
package pool

// StringPool deduplicates strings and assigns sequential integer indices.
type StringPool struct {
	pool    map[string]int
	counter int
}

// New returns an empty StringPool.
func New() *StringPool {
	return &StringPool{pool: make(map[string]int)}
}

// Add inserts s into the pool (if not already present) and returns its index.
// Returns -1 when s is empty, indicating absence.
func (sp *StringPool) Add(s string) int {
	if s == "" {
		return -1
	}
	if idx, ok := sp.pool[s]; ok {
		return idx
	}
	idx := sp.counter
	sp.pool[s] = idx
	sp.counter++
	return idx
}

// GetArray returns the pool contents as a positionally ordered slice.
func (sp *StringPool) GetArray() []string {
	arr := make([]string, len(sp.pool))
	for s, idx := range sp.pool {
		arr[idx] = s
	}
	return arr
}

// Size returns the number of unique strings in the pool.
func (sp *StringPool) Size() int { return len(sp.pool) }

// ByteSize returns the total UTF-8 byte count of pooled strings.
func (sp *StringPool) ByteSize() int {
	n := 0
	for s := range sp.pool {
		n += len(s)
	}
	return n
}
