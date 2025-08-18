# Spector File Context Integration - Technical Research Report

## Executive Summary

This document provides comprehensive research and implementation guidance for creating a "Send to Spector" Windows context menu integration that allows users to right-click files and send them to an AI agent using OpenAI-compatible APIs. The system supports multiple file formats including DOCX, PDF, PPT, TXT, and others, with a dropdown interface similar to the Ghostman app's search feature.

## User Requirements

- **File Support**: DOCX, PDF, PPT, TXT, and other common formats
- **Context Menu Integration**: Right-click "Send to Spector" option
- **Interactive Interface**: Dropdown UI similar to Ghostman search feature
- **File Management**: Add/remove files before sending
- **Prompt Input**: Text box for user messages
- **One-Click Send**: Automated processing after user clicks send
- **OpenAI API Compatibility**: Works with any OpenAI-compatible endpoint

## Technical Architecture

### 1. Windows Shell Integration Methods

#### Method A: Send To Folder Integration (Recommended)
- **Location**: `%APPDATA%\Microsoft\Windows\SendTo` (accessible via `shell:sendto`)
- **Implementation**: Place shortcuts to Python scripts in SendTo folder
- **Advantages**: 
  - No registry modifications required
  - No administrator privileges needed
  - Immediate availability after installation
  - Easy to install/uninstall
  - Works with all file types automatically
- **Access**: Right-click any file → "Send to" → "📤 Send to Spector"

#### SendTo Folder Implementation

```python
import os
import sys
from pathlib import Path
import win32com.client

class SendToInstaller:
    """Handles SendTo folder integration for Spector."""
    
    def __init__(self):
        # Get SendTo folder path
        self.sendto_folder = Path(os.path.expandvars(r'%APPDATA%\Microsoft\Windows\SendTo'))
        self.shortcut_name = "📤 Send to Spector.lnk"
        self.shortcut_path = self.sendto_folder / self.shortcut_name
    
    def create_sendto_shortcut(self, target_script_path, icon_path=None):
        """Create a shortcut in the SendTo folder."""
        try:
            # Create COM object for shell
            shell = win32com.client.Dispatch("WScript.Shell")
            
            # Create shortcut
            shortcut = shell.CreateShortCut(str(self.shortcut_path))
            shortcut.Targetpath = sys.executable  # Python executable
            shortcut.Arguments = f'"{target_script_path}"'  # Script to run
            shortcut.WorkingDirectory = str(Path(target_script_path).parent)
            shortcut.Description = "Send files to Spector AI for analysis"
            
            # Set icon if provided
            if icon_path and Path(icon_path).exists():
                shortcut.IconLocation = str(icon_path)
            
            # Save shortcut
            shortcut.save()
            
            print(f"✅ SendTo shortcut created: {self.shortcut_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create SendTo shortcut: {e}")
            return False
    
    def remove_sendto_shortcut(self):
        """Remove the SendTo shortcut."""
        try:
            if self.shortcut_path.exists():
                self.shortcut_path.unlink()
                print(f"✅ SendTo shortcut removed: {self.shortcut_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to remove SendTo shortcut: {e}")
            return False
    
    def is_installed(self):
        """Check if SendTo shortcut exists."""
        return self.shortcut_path.exists()

# Alternative simple batch file approach (no dependencies)
class SimpleSendToInstaller:
    """Simple SendTo installation using batch files."""
    
    def __init__(self):
        self.sendto_folder = Path(os.path.expandvars(r'%APPDATA%\Microsoft\Windows\SendTo'))
        self.batch_name = "📤 Send to Spector.bat"
        self.batch_path = self.sendto_folder / self.batch_name
    
    def create_sendto_batch(self, target_script_path):
        """Create a batch file in SendTo folder."""
        try:
            # Create batch file content
            batch_content = f'''@echo off
cd /d "{Path(target_script_path).parent}"
"{sys.executable}" "{target_script_path}" %*
'''
            
            # Write batch file
            with open(self.batch_path, 'w') as f:
                f.write(batch_content)
            
            print(f"✅ SendTo batch file created: {self.batch_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create SendTo batch file: {e}")
            return False
```

### 2. File Format Support

#### Supported File Types and Processing Methods

| Format | Extension | Processing Library | API Support |
|--------|-----------|-------------------|-------------|
| PDF | .pdf | Native OpenAI API | ✅ Direct upload (100 pages/32MB) |
| Word Documents | .docx | python-docx | ✅ Text extraction |
| PowerPoint | .pptx | python-pptx | ✅ Text/image extraction |
| Text Files | .txt, .md | Built-in | ✅ Direct reading |
| Code Files | .py, .js, .html, .css | Built-in | ✅ Syntax highlighting |
| Images | .jpg, .png, .gif | PIL/base64 | ✅ Vision API support |
| Excel | .xlsx | openpyxl | ✅ Data extraction |

#### File Processing Implementation

```python
import os
from pathlib import Path
from docx import Document
from pptx import Presentation
import base64
import json

class FileProcessor:
    def __init__(self):
        self.supported_formats = {
            '.txt': self._process_text,
            '.md': self._process_text,
            '.py': self._process_code,
            '.js': self._process_code,
            '.html': self._process_code,
            '.css': self._process_code,
            '.docx': self._process_docx,
            '.pptx': self._process_pptx,
            '.pdf': self._process_pdf,
            '.jpg': self._process_image,
            '.jpeg': self._process_image,
            '.png': self._process_image,
            '.gif': self._process_image,
        }
    
    def process_file(self, file_path):
        """Process a single file and return structured content"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension not in self.supported_formats:
            return {
                'type': 'unsupported',
                'name': path.name,
                'error': f'Unsupported file type: {extension}'
            }
        
        try:
            return self.supported_formats[extension](path)
        except Exception as e:
            return {
                'type': 'error',
                'name': path.name,
                'error': str(e)
            }
    
    def _process_text(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            'type': 'text',
            'name': path.name,
            'content': content,
            'size': len(content)
        }
    
    def _process_code(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            'type': 'code',
            'name': path.name,
            'content': content,
            'language': path.suffix[1:],
            'size': len(content)
        }
    
    def _process_docx(self, path):
        doc = Document(path)
        text_content = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        return {
            'type': 'document',
            'name': path.name,
            'content': '\n'.join(text_content),
            'paragraphs': len(text_content),
            'size': len('\n'.join(text_content))
        }
    
    def _process_pptx(self, path):
        prs = Presentation(path)
        slides_content = []
        
        for i, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)
            
            if slide_text:
                slides_content.append({
                    'slide_number': i + 1,
                    'content': '\n'.join(slide_text)
                })
        
        return {
            'type': 'presentation',
            'name': path.name,
            'slides': slides_content,
            'slide_count': len(slides_content),
            'total_content': '\n\n'.join([slide['content'] for slide in slides_content])
        }
    
    def _process_pdf(self, path):
        # For OpenAI API, we can send PDFs directly
        return {
            'type': 'pdf',
            'name': path.name,
            'path': str(path),
            'size': path.stat().st_size,
            'direct_upload': True
        }
    
    def _process_image(self, path):
        with open(path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        
        return {
            'type': 'image',
            'name': path.name,
            'content': encoded,
            'mime_type': f"image/{path.suffix[1:]}",
            'size': path.stat().st_size
        }
```

### 3. OpenAI API Integration

#### Modern API Capabilities (2024/2025)
- **Native PDF Support**: Direct upload without preprocessing
- **Multimodal Processing**: Text + images in single request
- **Context Window**: Up to 128k tokens (≈200 pages)
- **File Limits**: 100 pages, 32MB per request

#### API Client Implementation

```python
import openai
from typing import List, Dict

class SpectorAPIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o"):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
    
    def send_files_to_ai(self, files_content: List[Dict], user_prompt: str):
        """Send processed files to AI with user prompt"""
        messages = [
            {
                "role": "system",
                "content": "You are Spector, an AI assistant that analyzes files and provides insights."
            },
            {
                "role": "user",
                "content": self._build_message_content(files_content, user_prompt)
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4000,
                temperature=0.7
            )
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'usage': response.usage._asdict() if response.usage else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_message_content(self, files_content: List[Dict], prompt: str):
        """Build multimodal message content"""
        content = [{"type": "text", "text": prompt}]
        
        for file_info in files_content:
            if file_info['type'] in ['text', 'code']:
                language = file_info.get('language', '')
                content.append({
                    "type": "text",
                    "text": f"\n\n**File: {file_info['name']}**\n```{language}\n{file_info['content']}\n```"
                })
            
            elif file_info['type'] == 'document':
                content.append({
                    "type": "text",
                    "text": f"\n\n**Document: {file_info['name']}**\n{file_info['content']}"
                })
            
            elif file_info['type'] == 'presentation':
                slides_text = ""
                for slide in file_info['slides']:
                    slides_text += f"\n**Slide {slide['slide_number']}:**\n{slide['content']}\n"
                
                content.append({
                    "type": "text",
                    "text": f"\n\n**Presentation: {file_info['name']}**{slides_text}"
                })
            
            elif file_info['type'] == 'image':
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{file_info['mime_type']};base64,{file_info['content']}"
                    }
                })
            
            elif file_info['type'] == 'pdf' and file_info.get('direct_upload'):
                # Handle PDF direct upload
                content.append({
                    "type": "text",
                    "text": f"\n\n**PDF Document: {file_info['name']}** (Direct upload - content will be processed by AI)"
                })
        
        return content
```

### 4. User Interface Design (Ghostman-Style Dropdown)

#### UI Requirements Based on Ghostman Search Feature
- **Dropdown Interface**: Similar to search functionality
- **File List Management**: Add/remove files dynamically
- **Prompt Input**: Multi-line text area
- **Progress Indicators**: Loading states and feedback
- **Response Display**: Formatted AI response

#### Tkinter Implementation

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading

class SpectorDropdownInterface:
    def __init__(self, initial_files=None):
        self.initial_files = initial_files or []
        self.files_list = list(self.initial_files)
        self.file_processor = FileProcessor()
        self.api_client = None
        
        self.setup_main_window()
        self.load_configuration()
    
    def setup_main_window(self):
        """Create main dropdown-style window"""
        self.root = tk.Tk()
        self.root.title("Send to Spector")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Configure style for modern look
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        self.populate_initial_files()
    
    def create_widgets(self):
        """Create all UI widgets"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Files section
        ttk.Label(main_frame, text="Files to send:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Files listbox with scrollbar
        files_frame = ttk.Frame(main_frame)
        files_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        self.files_listbox = tk.Listbox(files_frame, height=8, selectmode=tk.EXTENDED)
        self.files_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        files_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.files_listbox.configure(yscrollcommand=files_scrollbar.set)
        
        # File management buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all_files).pack(side=tk.LEFT)
        
        # Prompt section
        ttk.Label(main_frame, text="Your message:", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(main_frame, height=6, wrap=tk.WORD)
        self.prompt_text.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.prompt_text.insert(1.0, "Please analyze these files and provide insights.")
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure API button
        ttk.Button(action_frame, text="Configure API", command=self.configure_api).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(action_frame, textvariable=self.progress_var)
        self.progress_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Send button (prominent)
        self.send_button = ttk.Button(action_frame, text="Send to Spector", 
                                    command=self.send_to_spector, style='Accent.TButton')
        self.send_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Cancel button
        ttk.Button(action_frame, text="Cancel", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def populate_initial_files(self):
        """Add initial files to the list"""
        for file_path in self.initial_files:
            self.add_file_to_list(file_path)
    
    def add_file_to_list(self, file_path):
        """Add a file to the listbox"""
        path = Path(file_path)
        display_name = f"{path.name} ({self.format_file_size(path.stat().st_size)})"
        self.files_listbox.insert(tk.END, display_name)
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def add_files(self):
        """Open file dialog to add more files"""
        filetypes = [
            ("All supported", "*.txt;*.docx;*.pptx;*.pdf;*.py;*.js;*.html;*.css;*.md;*.jpg;*.png;*.gif"),
            ("Text files", "*.txt;*.md"),
            ("Documents", "*.docx;*.pdf"),
            ("Presentations", "*.pptx"),
            ("Code files", "*.py;*.js;*.html;*.css"),
            ("Images", "*.jpg;*.jpeg;*.png;*.gif"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Select files to add",
            filetypes=filetypes
        )
        
        for file_path in files:
            if file_path not in self.files_list:
                self.files_list.append(file_path)
                self.add_file_to_list(file_path)
    
    def remove_selected_files(self):
        """Remove selected files from the list"""
        selected_indices = self.files_listbox.curselection()
        
        # Remove in reverse order to maintain indices
        for index in reversed(selected_indices):
            self.files_listbox.delete(index)
            if index < len(self.files_list):
                del self.files_list[index]
    
    def clear_all_files(self):
        """Clear all files from the list"""
        self.files_listbox.delete(0, tk.END)
        self.files_list.clear()
    
    def configure_api(self):
        """Open API configuration dialog"""
        config_window = APIConfigDialog(self.root, self.config)
        self.root.wait_window(config_window.window)
        self.load_configuration()
    
    def load_configuration(self):
        """Load API configuration"""
        config_path = Path.home() / ".spector_config.json"
        self.config = {
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o"
        }
        
        if config_path.exists():
            try:
                import json
                with open(config_path) as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Config load error: {e}")
        
        # Initialize API client if configured
        if self.config.get("api_key"):
            self.api_client = SpectorAPIClient(
                api_key=self.config["api_key"],
                base_url=self.config["base_url"],
                model=self.config["model"]
            )
    
    def send_to_spector(self):
        """Process files and send to AI"""
        if not self.files_list:
            messagebox.showwarning("No Files", "Please add at least one file to send.")
            return
        
        if not self.api_client:
            messagebox.showerror("API Not Configured", 
                               "Please configure your API settings first.")
            return
        
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if not prompt:
            messagebox.showwarning("No Message", "Please enter a message.")
            return
        
        # Disable send button and show progress
        self.send_button.configure(state='disabled')
        self.progress_var.set("Processing files...")
        
        # Process in background thread
        thread = threading.Thread(target=self._process_and_send, args=(prompt,))
        thread.daemon = True
        thread.start()
    
    def _process_and_send(self, prompt):
        """Background processing and API call"""
        try:
            # Process files
            self.root.after(0, lambda: self.progress_var.set("Processing files..."))
            processed_files = []
            
            for file_path in self.files_list:
                result = self.file_processor.process_file(file_path)
                processed_files.append(result)
            
            # Send to AI
            self.root.after(0, lambda: self.progress_var.set("Sending to AI..."))
            response = self.api_client.send_files_to_ai(processed_files, prompt)
            
            # Show results
            self.root.after(0, lambda: self._show_results(response))
            
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, lambda: (
                self.send_button.configure(state='normal'),
                self.progress_var.set("Ready")
            ))
    
    def _show_results(self, response):
        """Display AI response"""
        if response['success']:
            ResponseWindow(self.root, response['response'], response.get('usage'))
        else:
            messagebox.showerror("API Error", f"Failed to get response: {response['error']}")
    
    def _show_error(self, error_message):
        """Display error message"""
        messagebox.showerror("Error", f"Processing failed: {error_message}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

class APIConfigDialog:
    def __init__(self, parent, current_config):
        self.config = current_config.copy()
        self.window = tk.Toplevel(parent)
        self.window.title("API Configuration")
        self.window.geometry("400x250")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API Key
        ttk.Label(main_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.api_key_var = tk.StringVar(value=self.config.get("api_key", ""))
        api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Base URL
        ttk.Label(main_frame, text="Base URL:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.base_url_var = tk.StringVar(value=self.config.get("base_url", "https://api.openai.com/v1"))
        base_url_entry = ttk.Entry(main_frame, textvariable=self.base_url_var, width=50)
        base_url_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Model
        ttk.Label(main_frame, text="Model:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.model_var = tk.StringVar(value=self.config.get("model", "gpt-4o"))
        model_entry = ttk.Entry(main_frame, textvariable=self.model_var, width=50)
        model_entry.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=6, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(btn_frame, text="Save", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT)
        
        main_frame.columnconfigure(0, weight=1)
    
    def save_config(self):
        import json
        self.config.update({
            "api_key": self.api_key_var.get(),
            "base_url": self.base_url_var.get(),
            "model": self.model_var.get()
        })
        
        config_path = Path.home() / ".spector_config.json"
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        messagebox.showinfo("Success", "Configuration saved!")
        self.window.destroy()

class ResponseWindow:
    def __init__(self, parent, response_text, usage_info=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Spector Response")
        self.window.geometry("800x600")
        
        self.create_widgets(response_text, usage_info)
    
    def create_widgets(self, response_text, usage_info):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Response text
        self.text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_widget.insert(1.0, response_text)
        self.text_widget.configure(state='disabled')
        
        # Bottom frame with usage info and buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        if usage_info:
            usage_text = f"Tokens: {usage_info.get('total_tokens', 'N/A')} | " \
                        f"Prompt: {usage_info.get('prompt_tokens', 'N/A')} | " \
                        f"Completion: {usage_info.get('completion_tokens', 'N/A')}"
            ttk.Label(bottom_frame, text=usage_text, font=('Segoe UI', 8)).pack(side=tk.LEFT)
        
        ttk.Button(bottom_frame, text="Copy", command=self.copy_response).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(bottom_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)
    
    def copy_response(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(self.text_widget.get(1.0, tk.END))
        messagebox.showinfo("Copied", "Response copied to clipboard!")
```

### 5. Installation and Deployment

#### Installation Script

```python
# install_spector.py
import winreg as reg
import sys
import os
import shutil
from pathlib import Path

class SpectorInstaller:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.install_dir = Path.home() / "AppData" / "Local" / "Spector"
        
    def install(self):
        """Complete installation process"""
        print("🚀 Installing Spector File Context Integration...")
        
        try:
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files
            self._copy_files()
            
            # Install dependencies
            self._install_dependencies()
            
            # Register context menu
            self._register_context_menu()
            
            # Create desktop shortcut (optional)
            self._create_shortcuts()
            
            print("✅ Installation completed successfully!")
            print(f"📁 Installed to: {self.install_dir}")
            print("🖱️ Right-click any file and select '📤 Send to Spector'")
            
        except Exception as e:
            print(f"❌ Installation failed: {e}")
            return False
        
        return True
    
    def _copy_files(self):
        """Copy necessary files to installation directory"""
        files_to_copy = [
            "spector_handler.py",
            "file_processor.py", 
            "api_client.py",
            "spector_ui.py"
        ]
        
        for filename in files_to_copy:
            src = self.script_dir / filename
            if src.exists():
                shutil.copy2(src, self.install_dir / filename)
                print(f"📄 Copied {filename}")
    
    def _install_dependencies(self):
        """Install required Python packages"""
        packages = [
            "openai",
            "python-docx", 
            "python-pptx",
            "openpyxl",
            "pillow"
        ]
        
        for package in packages:
            os.system(f"pip install {package}")
            print(f"📦 Installed {package}")
    
    def _register_context_menu(self):
        """Register Windows context menu"""
        try:
            python_exe = sys.executable
            handler_script = self.install_dir / "spector_handler.py"
            
            # Register for all files
            key = reg.CreateKey(reg.HKEY_CLASSES_ROOT, r'*\shell\SendToSpector')
            reg.SetValue(key, '', reg.REG_SZ, '📤 Send to Spector')
            
            cmd_key = reg.CreateKey(key, 'command')
            command = f'"{python_exe}" "{handler_script}" "%1"'
            reg.SetValue(cmd_key, '', reg.REG_SZ, command)
            
            print("🔧 Context menu registered")
            
        except PermissionError:
            print("⚠️ Run as administrator to register context menu")
            raise
    
    def _create_shortcuts(self):
        """Create desktop and start menu shortcuts"""
        # Implementation for creating shortcuts
        pass
    
    def uninstall(self):
        """Remove Spector integration"""
        try:
            # Remove context menu
            reg.DeleteKey(reg.HKEY_CLASSES_ROOT, r'*\shell\SendToSpector\command')
            reg.DeleteKey(reg.HKEY_CLASSES_ROOT, r'*\shell\SendToSpector')
            
            # Remove installation directory
            shutil.rmtree(self.install_dir, ignore_errors=True)
            
            print("✅ Spector uninstalled successfully")
            
        except Exception as e:
            print(f"❌ Uninstall failed: {e}")

if __name__ == "__main__":
    installer = SpectorInstaller()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        installer.uninstall()
    else:
        installer.install()
```

### 6. OpenAI-Compatible API Support

#### Local LLM Integration

```python
class LocalLLMSupport:
    """Support for local LLM providers"""
    
    PROVIDERS = {
        "ollama": {
            "default_url": "http://localhost:11434/v1",
            "models": ["llama2", "codellama", "mistral"]
        },
        "lm_studio": {
            "default_url": "http://localhost:1234/v1", 
            "models": ["custom"]
        },
        "text-generation-webui": {
            "default_url": "http://localhost:5000/v1",
            "models": ["custom"]
        }
    }
    
    @classmethod
    def get_provider_config(cls, provider_name):
        return cls.PROVIDERS.get(provider_name, {})
    
    @classmethod
    def test_connection(cls, base_url, api_key="dummy"):
        """Test connection to local LLM"""
        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            response = client.models.list()
            return True, list(response.data)
        except Exception as e:
            return False, str(e)
```

## Implementation Roadmap

### Phase 1: Core Functionality (Week 1)
- [ ] Basic file processing for TXT, DOCX, PDF, PPT
- [ ] Simple context menu registration
- [ ] Basic UI with file list and prompt input
- [ ] OpenAI API integration

### Phase 2: Enhanced UI (Week 2)  
- [ ] Ghostman-style dropdown interface
- [ ] File add/remove functionality
- [ ] Progress indicators and loading states
- [ ] Response formatting and display

### Phase 3: Advanced Features (Week 3)
- [ ] Local LLM support
- [ ] Configuration management
- [ ] Error handling and recovery
- [ ] Performance optimization

### Phase 4: Polish and Deployment (Week 4)
- [ ] Installation/uninstallation scripts
- [ ] User documentation
- [ ] Testing across file types
- [ ] Performance tuning

## Security Considerations

### API Key Protection
- Store encrypted configuration files
- Use Windows credential manager for sensitive data
- Implement secure key derivation

### File Access Security
- Validate file paths to prevent directory traversal
- Implement file size limits
- Scan for malicious content patterns

### Network Security
- Certificate verification for HTTPS connections
- Request timeout handling
- Rate limiting for API calls

## Performance Optimization

### File Processing
- Async file reading for large documents
- Lazy loading of file content
- Progress callbacks for user feedback

### API Efficiency
- Request batching for multiple files
- Content compression before sending
- Token usage monitoring and optimization

### Memory Management
- Streaming file processing for large files
- Garbage collection optimization
- Resource cleanup after processing

## Testing Strategy

### Unit Testing
```python
# test_file_processor.py
import unittest
from file_processor import FileProcessor

class TestFileProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = FileProcessor()
    
    def test_text_file_processing(self):
        # Test implementation
        pass
    
    def test_docx_processing(self):
        # Test implementation  
        pass
    
    def test_unsupported_format(self):
        # Test implementation
        pass
```

### Integration Testing
- Test with various file types and sizes
- API compatibility testing with different providers
- UI responsiveness testing
- Context menu registration verification

### User Acceptance Testing
- File selection workflow testing
- Prompt input and response display
- Error handling and recovery scenarios
- Performance with large files

## Troubleshooting Guide

### Common Issues

1. **Context Menu Not Appearing**
   - Check registry entries
   - Verify Python path in command
   - Run installer as administrator

2. **API Connection Failures**
   - Verify API key and URL
   - Check network connectivity
   - Test with simple API call

3. **File Processing Errors**
   - Check file format support
   - Verify file permissions
   - Handle corrupted files gracefully

4. **Performance Issues**
   - Monitor memory usage
   - Implement file size limits
   - Optimize API request batching

## Future Enhancements

### Advanced Features
- **Batch Processing**: Handle multiple file sets
- **Template System**: Pre-defined prompt templates
- **History Tracking**: Save previous interactions
- **Plugin Architecture**: Extensible file type support

### Integration Possibilities
- **Cloud Storage**: Direct integration with Google Drive, OneDrive
- **Version Control**: Git integration for code files
- **Collaboration**: Share processed results with teams
- **Analytics**: Usage tracking and optimization insights

---

# ARCHITECTURAL DESIGN & CODE STRUCTURE

*Based on analysis by Python Expert and Code Architect agents*

## Recommended Code Architecture

### Directory Structure Integration with Ghostman

```
ghostman/
├── src/
│   ├── infrastructure/
│   │   ├── ai/                     # ✅ Existing - Reuse API client
│   │   ├── storage/                # ✅ Existing - Reuse settings
│   │   ├── logging/                # ✅ Existing - Reuse logging
│   │   └── spector/                # 🆕 New Integration Module
│   │       ├── __init__.py
│   │       ├── file_processing/
│   │       │   ├── __init__.py
│   │       │   ├── processors.py    # File type handlers
│   │       │   ├── validators.py    # Security validation
│   │       │   └── extractors.py    # Content extraction
│   │       ├── ui/
│   │       │   ├── __init__.py
│   │       │   ├── context_dialog.py   # Dropdown interface
│   │       │   ├── progress_window.py  # Processing feedback
│   │       │   └── response_viewer.py  # AI response display
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── integration_service.py  # Main orchestrator
│   │       │   ├── batch_processor.py      # Multi-file handling
│   │       │   └── history_service.py      # Processing history
│   │       └── shell/
│   │           ├── __init__.py
│   │           ├── sendto_manager.py       # SendTo folder integration
│   │           ├── context_handler.py      # Entry point script
│   │           └── installer.py            # Installation logic
├── assets/
│   ├── icons/
│   │   └── spector_context.ico     # 🆕 Context menu icon
│   └── installers/                 # 🆕 Installation scripts
│       ├── install_spector.py
│       ├── uninstall_spector.py
│       └── spector_launcher.bat
└── scripts/
    ├── build_spector.py            # 🆕 Spector-specific build
    └── package_integration.py      # 🆕 Deployment script
```

## Python Architecture Design

### 1. Core Application Layer

```python
# core/application.py
from typing import List, Optional
import asyncio
from dataclasses import dataclass

from .config import ConfigManager
from ..domain.services.file_processor import FileProcessorService
from ..domain.services.analysis_service import AnalysisService
from ..presentation.controllers.main_controller import MainController

@dataclass
class AppContext:
    """Application context containing shared services."""
    config: ConfigManager
    file_processor: FileProcessorService
    analysis_service: AnalysisService
    main_controller: Optional[MainController] = None

class SpectorApplication:
    """Main application coordinator following the Application Service pattern."""
    
    def __init__(self):
        self.context = self._initialize_context()
        self.is_running = False
    
    def _initialize_context(self) -> AppContext:
        """Initialize application context with all services."""
        config = ConfigManager()
        file_processor = FileProcessorService(config)
        analysis_service = AnalysisService(config)
        
        return AppContext(
            config=config,
            file_processor=file_processor,
            analysis_service=analysis_service
        )
    
    async def start_gui(self, initial_files: List[str] = None):
        """Start the GUI application."""
        from ..presentation.controllers.main_controller import MainController
        
        self.context.main_controller = MainController(self.context)
        self.is_running = True
        
        if initial_files:
            await self.context.main_controller.load_files(initial_files)
        
        await self.context.main_controller.run()
    
    def install_sendto_integration(self):
        """Install SendTo folder integration."""
        from ..infrastructure.shell.sendto_manager import SendToInstaller
        installer = SendToInstaller()
        handler_script = Path(__file__).parent / "shell" / "context_handler.py"
        installer.create_sendto_shortcut(str(handler_script))
```

### 2. Abstract File Processing System

```python
# domain/processors/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProcessingResult:
    """Result of file processing operation."""
    success: bool
    content: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None
    file_path: Path = None

class FileProcessor(ABC):
    """Abstract base class for file processors."""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        pass
    
    @abstractmethod
    async def process(self, file_path: Path) -> ProcessingResult:
        """Process a single file and extract content."""
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """Validate if file can be processed."""
        pass

# domain/processors/factory.py
class ProcessorFactory:
    """Factory for creating appropriate file processors."""
    
    def __init__(self):
        self._processors: Dict[str, Type[FileProcessor]] = {}
        self._register_default_processors()
    
    def register_processor(self, processor_class: Type[FileProcessor]):
        """Register a new processor type."""
        processor_instance = processor_class()
        for ext in processor_instance.supported_extensions:
            self._processors[ext.lower()] = processor_class
    
    def get_processor(self, file_path: Path) -> Optional[FileProcessor]:
        """Get appropriate processor for file."""
        extension = file_path.suffix.lower()
        processor_class = self._processors.get(extension)
        
        if processor_class:
            return processor_class()
        return None
```

### 3. API Client Architecture

```python
# infrastructure/api/client.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

@dataclass
class APIMessage:
    """Represents a message in the API conversation."""
    role: str  # 'user', 'assistant', 'system'
    content: str

@dataclass
class APIResponse:
    """Response from API service."""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

class APIClient(ABC):
    """Abstract base class for API clients."""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[APIMessage],
        model: str = None,
        stream: bool = False,
        **kwargs
    ) -> APIResponse:
        """Send chat completion request."""
        pass
    
    @abstractmethod
    async def get_models(self) -> List[str]:
        """Get available models."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if API is available."""
        pass
```

### 4. Ghostman Integration Layer

```python
# Extend existing SettingsManager
class SpectorSettingsExtension:
    """Extend Ghostman settings for Spector integration."""
    
    SPECTOR_DEFAULTS = {
        'spector': {
            'enabled': True,
            'file_size_limit_mb': 32,
            'supported_formats': ['.docx', '.pdf', '.pptx', '.txt', '.py', '.js'],
            'processing_timeout': 30,
            'batch_size_limit': 10
        },
        'spector_ui': {
            'theme_integration': True,
            'progress_notifications': True,
            'remember_window_position': True
        }
    }

# Leverage existing AI infrastructure
class SpectorAIService:
    """Spector-specific AI service using Ghostman infrastructure."""
    
    def __init__(self, settings_manager):
        from ...ai.api_client import OpenAICompatibleClient
        
        # Reuse existing settings and client
        self.settings = settings_manager
        api_key = self.settings.get('ai.api_key')
        base_url = self.settings.get('ai.base_url', 'https://api.openai.com/v1')
        
        self.client = OpenAICompatibleClient(
            base_url=base_url,
            api_key=api_key
        )

# Theme system integration
class SpectorThemeIntegration:
    """Apply Ghostman themes to Spector UI components."""
    
    def __init__(self, theme_manager):
        self.theme_manager = theme_manager
        self.current_colors = theme_manager.get_current_theme()
    
    def apply_to_tkinter_window(self, window):
        """Apply current Ghostman theme to tkinter window."""
        colors = self.current_colors
        window.configure(bg=colors.get('background'))
        self._apply_recursive(window, colors)
```

### 5. Security Architecture

```python
class FileSecurityValidator:
    """Security validation for file processing."""
    
    ALLOWED_EXTENSIONS = {'.docx', '.pdf', '.pptx', '.txt', '.py', '.js', '.html', '.css', '.md'}
    MAX_FILE_SIZE = 32 * 1024 * 1024  # 32MB
    SUSPICIOUS_PATTERNS = [
        r'<script\s+.*?>',  # Script tags
        r'javascript:',     # JavaScript URIs
        r'vbscript:',       # VBScript URIs
    ]
    
    @classmethod
    def validate_file(cls, file_path):
        """Comprehensive file validation."""
        path = Path(file_path)
        
        # Path traversal prevention
        if '..' in str(path) or str(path).startswith(('\\\\', '//')):
            raise SecurityError("Path traversal detected")
        
        # Extension validation
        if path.suffix.lower() not in cls.ALLOWED_EXTENSIONS:
            raise SecurityError(f"File type not allowed: {path.suffix}")
        
        # Size validation
        if path.stat().st_size > cls.MAX_FILE_SIZE:
            raise SecurityError("File too large")
        
        return True

# Reuse existing encryption from SettingsManager
class SpectorSecurityManager:
    """Security management for Spector integration."""
    
    def __init__(self, settings_manager):
        self.settings = settings_manager  # Already has encryption
    
    def store_api_config(self, api_key, base_url):
        """Store API configuration securely."""
        # Leverage existing encryption in SettingsManager
        self.settings.set('spector.api_key', api_key)  # Auto-encrypted
        self.settings.set('spector.base_url', base_url)
```

### 6. Installation & SendTo Folder Management

```python
class SpectorInstaller:
    """Professional installation system for Spector integration using SendTo folder."""
    
    def __init__(self):
        self.ghostman_dir = self._find_ghostman_installation()
        self.install_dir = Path.home() / "AppData" / "Local" / "Ghostman" / "Spector"
        self.sendto_installer = SendToInstaller()
    
    def install(self):
        """Complete installation process."""
        steps = [
            ("Validating environment", self._validate_environment),
            ("Creating directories", self._create_directories),
            ("Installing files", self._install_files),
            ("Creating SendTo shortcut", self._create_sendto_integration),
            ("Configuring integration", self._configure_integration),
            ("Running tests", self._run_installation_tests)
        ]
        
        for description, step_func in steps:
            self._log_step(description)
            try:
                step_func()
                self._log_success(description)
            except Exception as e:
                self._log_error(description, e)
                return False
        
        return True
    
    def _create_sendto_integration(self):
        """Create SendTo folder integration."""
        handler_script = self.install_dir / "context_handler.py"
        icon_path = self.install_dir / "assets" / "spector_icon.ico"
        
        # Try creating shortcut first (preferred method)
        try:
            success = self.sendto_installer.create_sendto_shortcut(
                str(handler_script), 
                str(icon_path) if icon_path.exists() else None
            )
            if success:
                return
        except ImportError:
            # win32com not available, fall back to batch file
            pass
        
        # Fallback to batch file method
        simple_installer = SimpleSendToInstaller()
        success = simple_installer.create_sendto_batch(str(handler_script))
        
        if not success:
            raise InstallationError("Failed to create SendTo integration")
    
    def uninstall(self):
        """Remove Spector integration."""
        try:
            # Remove SendTo shortcut/batch file
            self.sendto_installer.remove_sendto_shortcut()
            
            # Also try to remove batch file if it exists
            simple_installer = SimpleSendToInstaller()
            if simple_installer.batch_path.exists():
                simple_installer.batch_path.unlink()
            
            # Remove installation directory
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir, ignore_errors=True)
            
            print("✅ Spector uninstalled successfully")
            return True
            
        except Exception as e:
            print(f"❌ Uninstall failed: {e}")
            return False
    
    def is_installed(self):
        """Check if Spector is installed."""
        return (self.sendto_installer.is_installed() or 
                SimpleSendToInstaller().batch_path.exists())
```

### 7. Configuration Schema

```python
# Unified Configuration Strategy
SPECTOR_CONFIG_SCHEMA = {
    'spector': {
        'enabled': bool,
        'installation_path': str,
        'registry_key': str,
        'auto_start': bool
    },
    'spector_processing': {
        'file_size_limit_mb': int,
        'batch_timeout_seconds': int,
        'supported_formats': list,
        'extract_images': bool,
        'preserve_formatting': bool
    },
    'spector_ai': {
        'use_ghostman_settings': bool,  # If True, inherit from main AI config
        'dedicated_api_key': str,       # Optional separate API key
        'model_override': str,          # Optional model override
        'temperature': float,
        'max_tokens': int
    },
    'spector_ui': {
        'theme_integration': bool,
        'window_position': dict,
        'show_progress': bool,
        'auto_close_after': int
    }
}
```

## Design Patterns Applied

1. **Repository Pattern**: For configuration and file management
2. **Factory Pattern**: For file processor creation
3. **Strategy Pattern**: For different file processing strategies
4. **Observer Pattern**: For GUI event handling
5. **Command Pattern**: For API operations
6. **Adapter Pattern**: For different API providers
7. **Dependency Injection**: Through the AppContext
8. **MVP/MVC**: Separation of GUI, controllers, and business logic

## Risk Assessment & Mitigation

| Risk Category | Risk Description | Mitigation Strategy |
|---------------|------------------|-------------------|
| **Security** | Malicious file processing | File validation, sandboxing, size limits |
| **Performance** | Large file processing lag | Async processing, progress feedback, timeouts |
| **Integration** | Conflict with Ghostman updates | Version compatibility checks, separate modules |
| **Installation** | SendTo folder access issues | Fallback batch file method, user folder permissions |

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- **Integration Module Setup**: Create `ghostman/src/infrastructure/spector/` structure
- **Settings Extension**: Extend SettingsManager with Spector configuration  
- **Basic File Processing**: Implement core file processors for TXT, DOCX, PDF
- **Security Framework**: File validation and basic security measures

### Phase 2: Core Features (Week 3-4)
- **SendTo Integration**: SendTo folder shortcut creation and handler script
- **AI Service Integration**: Leverage existing Ghostman AI infrastructure
- **Basic UI**: Simple tkinter interface with file selection and processing
- **Installation System**: Basic installer with SendTo folder management

### Phase 3: Enhanced Features (Week 5-6)
- **Advanced UI**: Theme integration, progress indicators, response viewer
- **Batch Processing**: Multiple file handling with async processing
- **History Integration**: Store processing history in Ghostman database
- **Error Handling**: Comprehensive error recovery and user feedback

### Phase 4: Polish & Deployment (Week 7-8)
- **Theme System Integration**: Full Ghostman theme compatibility
- **Performance Optimization**: Large file handling, memory management
- **Professional Installation**: MSI package, proper uninstallation
- **Documentation**: User guides, troubleshooting, API documentation

## Conclusion

This comprehensive technical guide provides the foundation for implementing a robust "Send to Spector" file context integration system. The modular architecture supports various file formats, OpenAI-compatible APIs, and provides a user-friendly interface similar to the Ghostman application's search feature.

The architecture design leverages existing Ghostman infrastructure while maintaining clear separation of concerns and providing enterprise-grade security and reliability features. The implementation prioritizes security, performance, and user experience while maintaining compatibility with both cloud-based and local LLM providers.