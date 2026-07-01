package tests

import (
	"testing"

	"sdd-compile/internal/pool"
)

func TestStringPoolDeduplication(t *testing.T) {
	sp := pool.New()
	idx1 := sp.Add("hello")
	idx2 := sp.Add("world")
	idx3 := sp.Add("hello")

	if idx1 != idx3 {
		t.Errorf("duplicate 'hello' should return same index: %d vs %d", idx1, idx3)
	}
	if idx1 == idx2 {
		t.Errorf("'hello' and 'world' should have different indices")
	}
}

func TestStringPoolEmpty(t *testing.T) {
	sp := pool.New()
	idx := sp.Add("")
	if idx != -1 {
		t.Errorf("empty string should return -1, got %d", idx)
	}
}

func TestStringPoolGetArray(t *testing.T) {
	sp := pool.New()
	sp.Add("a")
	sp.Add("b")
	sp.Add("c")
	arr := sp.GetArray()
	if len(arr) != 3 {
		t.Fatalf("expected 3 items, got %d", len(arr))
	}
}

func TestStringPoolSize(t *testing.T) {
	sp := pool.New()
	sp.Add("hello")
	sp.Add("world")
	sp.Add("hello")
	if sp.Size() != 2 {
		t.Errorf("expected 2 unique strings, got %d", sp.Size())
	}
}
