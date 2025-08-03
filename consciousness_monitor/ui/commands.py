"""Interactive command interface for user input during monitoring."""

import threading
import queue
import time
import select
import sys
from typing import Optional, Callable, Dict, Any

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class CommandInterface:
    """Handles interactive commands during monitoring."""
    
    def __init__(self):
        self.command_queue = queue.Queue()
        self.clipboard_queue = queue.Queue()
        self.active = True
        self.command_handlers = {}
        
        # Start command listener thread
        self.command_thread = threading.Thread(target=self._command_listener, daemon=True)
        self.command_thread.start()
        
        # Start clipboard handler thread if available
        if CLIPBOARD_AVAILABLE:
            self.clipboard_thread = threading.Thread(target=self._clipboard_handler, daemon=True)
            self.clipboard_thread.start()
    
    def register_handler(self, command: str, handler: Callable[[str], None]):
        """Register a command handler function."""
        self.command_handlers[command] = handler
    
    def _command_listener(self):
        """Listen for keyboard commands in a separate thread."""
        while self.active:
            try:
                if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.1)[0]:
                    command = sys.stdin.read(1).lower()
                    if command:
                        self.command_queue.put(command)
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
    
    def _clipboard_handler(self):
        """Handle clipboard operations in a separate thread."""
        while self.active:
            try:
                if not self.clipboard_queue.empty():
                    text = self.clipboard_queue.get_nowait()
                    if CLIPBOARD_AVAILABLE:
                        pyperclip.copy(text)
                        print("📋 Copied to clipboard")
                time.sleep(0.1)
            except:
                time.sleep(0.1)
    
    def check_for_commands(self) -> Optional[str]:
        """
        Check for pending commands.
        
        Returns:
            Command string if available, None otherwise
        """
        try:
            if not self.command_queue.empty():
                return self.command_queue.get_nowait()
        except:
            pass
        return None
    
    def copy_to_clipboard(self, text: str):
        """Queue text for clipboard copying."""
        if CLIPBOARD_AVAILABLE:
            self.clipboard_queue.put(text)
        else:
            print("📋 Clipboard not available")
    
    def process_command(self, command: str, context: Dict[str, Any] = None) -> bool:
        """
        Process a command.
        
        Args:
            command: Command character
            context: Optional context data for command handlers
            
        Returns:
            True if should continue monitoring, False to quit
        """
        if context is None:
            context = {}
        
        try:
            if command == 'q':
                print("👋 Exiting consciousness monitor...")
                return False
            
            elif command == 'c':
                # Copy recent events
                if 'copy_events' in self.command_handlers:
                    self.command_handlers['copy_events'](context)
                else:
                    print("📋 Copy function not available")
            
            elif command == 's':
                # Show session summary
                if 'show_summary' in self.command_handlers:
                    self.command_handlers['show_summary'](context)
                else:
                    print("📊 Summary function not available")
            
            elif command == 'n':
                # Force immediate output
                if 'force_output' in self.command_handlers:
                    self.command_handlers['force_output'](context)
                else:
                    print("⚡ Force output not available")
            
            elif command == 'h' or command == '?':
                self._show_help()
            
            elif command == 'd':
                # Toggle debug mode
                if 'toggle_debug' in self.command_handlers:
                    self.command_handlers['toggle_debug'](context)
                else:
                    print("🔍 Debug toggle not available")
            
            else:
                # Check for custom handlers
                if command in self.command_handlers:
                    self.command_handlers[command](context)
                else:
                    print(f"❓ Unknown command: '{command}' (press 'h' for help)")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Command processing error: {e}")
            return True
    
    def _show_help(self):
        """Display help information."""
        print("\n🎮 Available Commands:")
        print("  'c' - Copy recent events to clipboard")
        print("  's' - Show session summary")
        print("  'n' - Force immediate output")
        print("  'd' - Toggle debug mode")
        print("  'h' - Show this help")
        print("  'q' - Quit monitoring")
        
        # Show custom commands if any
        custom_commands = [cmd for cmd in self.command_handlers.keys() 
                          if cmd not in ['copy_events', 'show_summary', 'force_output', 'toggle_debug']]
        if custom_commands:
            print("  Custom commands:", ", ".join(f"'{cmd}'" for cmd in custom_commands))
        
        print()
    
    def shutdown(self):
        """Shutdown the command interface."""
        self.active = False
        
        # Wait for threads to finish
        if hasattr(self, 'command_thread') and self.command_thread.is_alive():
            self.command_thread.join(timeout=1.0)
        
        if hasattr(self, 'clipboard_thread') and self.clipboard_thread.is_alive():
            self.clipboard_thread.join(timeout=1.0)