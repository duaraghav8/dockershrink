package log

import (
	"log"
	"os"
)

type Logger struct {
	debugEnabled bool
}

// NewLogger creates a logger. If debug = true, debug messages are printed.
func NewLogger(debug bool) *Logger {
	return &Logger{debugEnabled: debug}
}

func (l *Logger) Debug(msg string, data map[string]interface{}) {
	if l.debugEnabled {
		l.printLog("DEBUG", msg, data)
	}
}

func (l *Logger) Info(msg string, data map[string]interface{}) {
	l.printLog("INFO", msg, data)
}

func (l *Logger) Warn(msg string, data map[string]interface{}) {
	l.printLog("WARN", msg, data)
}

func (l *Logger) Error(msg string, data map[string]interface{}) {
	l.printLog("ERROR", msg, data)
}

func (l *Logger) Fatal(msg string, data map[string]interface{}) {
	l.printLog("FATAL", msg, data)
	os.Exit(1)
}

func (l *Logger) printLog(level, msg string, data map[string]interface{}) {
	if data != nil && len(data) > 0 {
		log.Printf("[%s] %s | %v\n", level, msg, data)
	} else {
		log.Printf("[%s] %s\n", level, msg)
	}
}
