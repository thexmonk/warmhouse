package main

import (
	"encoding/json"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

type TemperatureResponse struct {
	Value       float64   `json:"value"`
	Unit        string    `json:"unit"`
	Timestamp   time.Time `json:"timestamp"`
	Location    string    `json:"location"`
	Status      string    `json:"status"`
	SensorID    string    `json:"sensor_id"`
	SensorType  string    `json:"sensor_type"`
	Description string    `json:"description"`
}

func main() {
	rand.Seed(time.Now().UnixNano())

	mux := http.NewServeMux()
	mux.HandleFunc("/temperature", temperatureByLocationHandler)
	mux.HandleFunc("/temperature/", temperatureByIDHandler)

	port := getPort()

	log.Printf("starting temperature-api on port %s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}

func getPort() string {
	if p := os.Getenv("PORT"); p != "" {
		return p
	}
	return "8081"
}

func temperatureByLocationHandler(w http.ResponseWriter, r *http.Request) {
	location := r.URL.Query().Get("location")
	sensorID := r.URL.Query().Get("sensorId")

	if location == "" {
		switch sensorID {
		case "1":
			location = "Living Room"
		case "2":
			location = "Bedroom"
		case "3":
			location = "Kitchen"
		default:
			location = "Unknown"
		}
	}

	if sensorID == "" {
		switch location {
		case "Living Room":
			sensorID = "1"
		case "Bedroom":
			sensorID = "2"
		case "Kitchen":
			sensorID = "3"
		default:
			sensorID = "0"
		}
	}

	writeTemperatureResponse(w, location, sensorID)
}

func temperatureByIDHandler(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/temperature/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		http.NotFound(w, r)
		return
	}

	sensorID := parts[0]
	location := sensorLocationFromID(sensorID)

	writeTemperatureResponse(w, location, sensorID)
}

func sensorLocationFromID(sensorID string) string {
	switch sensorID {
	case "1":
		return "Living Room"
	case "2":
		return "Bedroom"
	case "3":
		return "Kitchen"
	default:
		return "Unknown"
	}
}

func randomTemperature() float64 {
	min := -30.0
	max := 30.0
	return min + rand.Float64()*(max-min)
}

func writeTemperatureResponse(w http.ResponseWriter, location, sensorID string) {
	temp := randomTemperature()

	resp := TemperatureResponse{
		Value:       temp,
		Unit:        "C",
		Timestamp:   time.Now().UTC(),
		Location:    location,
		Status:      "ok",
		SensorID:    sensorID,
		SensorType:  "thermometer",
		Description: "Simulated temperature sensor reading",
	}

	w.Header().Set("Content-Type", "application/json")
	_ = strconv.FormatFloat(resp.Value, 'f', 2, 64)

	if err := json.NewEncoder(w).Encode(resp); err != nil {
		http.Error(w, "failed to encode response", http.StatusInternalServerError)
	}
}

