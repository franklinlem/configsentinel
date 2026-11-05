package server

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestMaintenanceRetriesAfterTemporaryFailure(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	calls := make(chan struct{}, 2)
	done := make(chan struct{})
	go func() {
		defer close(done)
		attempts := 0
		maintenanceLoop(ctx, 10*time.Millisecond, func(context.Context) error {
			attempts++
			calls <- struct{}{}
			if attempts == 1 {
				return errors.New("temporary database error")
			}
			cancel()
			return nil
		})
	}()
	select {
	case <-done:
		if len(calls) != 2 {
			t.Fatalf("expected failed run and retry, got %d attempts", len(calls))
		}
	case <-time.After(time.Second):
		t.Fatal("maintenance did not retry and stop")
	}
}

func TestMaintenanceCancelledBeforeStart(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	called := false
	maintenanceLoop(ctx, time.Millisecond, func(context.Context) error {
		called = true
		return nil
	})
	if called {
		t.Fatal("maintenance ran after cancellation")
	}
}
