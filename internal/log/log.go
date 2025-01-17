package log

import (
	"log"
	"os"

	"github.com/fatih/color"
)

type Logger struct {
	debugEnabled bool
	logger       *log.Logger
}

// NewLogger creates a logger. If debug = true, debug messages are printed.
func NewLogger(debug bool) *Logger {
	return &Logger{
		debugEnabled: debug,
		logger:       log.New(os.Stdout, "", 0),
	}
}

func (l *Logger) Debug(msg string, data map[string]string) {
	if !l.debugEnabled {
		return
	}
	l.logger.Printf("[DEBUG] %s\n", msg)
	for k, v := range data {
		l.logger.Printf("    %s=%s", k, v)
	}
}

func (l *Logger) Infof(format string, a ...any) {
	l.printf(color.FgGreen, format, a...)
}

func (l *Logger) Warnf(format string, a ...any) {
	l.printf(color.FgYellow, format, a...)
}

func (l *Logger) Errorf(format string, a ...any) {
	l.printf(color.FgRed, format, a...)
}

func (l *Logger) Fatalf(format string, a ...any) {
	l.Errorf(format, a...)
	os.Exit(1)
}

func (l *Logger) printf(c color.Attribute, format string, a ...any) {
	color.New(c).Printf(format+"\n", a...)
}
