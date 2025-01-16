package log

import (
	"log"
	"os"
)

// TODO
// - remove logger metadata from log messages, just keep the message
// - debug logs should be gray color to signify background stuff

type Logger struct {
	debugEnabled bool
}

// NewLogger creates a logger. If debug = true, debug messages are printed.
func NewLogger(debug bool) *Logger {
	return &Logger{debugEnabled: debug}
}

func (l *Logger) Debug(msg string, data map[string]string) {
	if l.debugEnabled {
		l.printLog("DEBUG", msg, data)
	}
}

func (l *Logger) Info(msg string, data map[string]string) {
	l.printLog("INFO", msg, data)
}

func (l *Logger) Warn(msg string, data map[string]string) {
	l.printLog("WARN", msg, data)
}

func (l *Logger) Error(msg string, data map[string]string) {
	l.printLog("ERROR", msg, data)
}

func (l *Logger) Fatal(msg string, data map[string]string) {
	l.printLog("FATAL", msg, data)
	os.Exit(1)
}

func (l *Logger) printLog(level, msg string, data map[string]string) {
	if data != nil && len(data) > 0 {
		log.Printf("[%s] %s\n", level, msg)
		for k, v := range data {
			log.Printf("    %s=%s", k, v)
		}
		log.Println("")
	} else {
		log.Printf("[%s] %s\n", level, msg)
	}
}
