// Default entrypoint: an HTTP server on port 8080. Copy this directory's
// Dockerfile to package your own Go service the same way.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"runtime"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"service": "golang",
			"message": "Hello from Go on a Datum unikernel",
			"go":      runtime.Version(),
			"path":    r.URL.Path,
		})
	})
	log.Printf("listening on :%s", port)
	// Unspecified host: dual-stack ([::] with IPv4-mapped fallback). Datum
	// compute networks are IPv6-only, so an IPv4-only bind is unreachable.
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
