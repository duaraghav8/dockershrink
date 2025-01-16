package log

import (
	"log"
	"os"
)

// TODO
// - remove logger metadata from log messages, just keep the message
// - debug logs should be gray color to signify background stuff
// - data should be map[string]string, print everything as key=value
//   - if some value is too long, print it in a separate line and give enough whitespace in between

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
