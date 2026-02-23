# Specter Skills System - Architecture Plan

## Overview

A **Skills System** that allows Specter to execute common desktop tasks automatically based on user intent. Designed for both technical and non-technical users with intuitive invocation methods.

---

## Core Design Principles

### 1. **User-Friendly Invocation (Multi-Modal)**
- **Natural Language**: Users can simply type "draft an email to John about the meeting"
- **Slash Commands**: `/email draft` for power users
- **GUI Buttons**: Skill palette in the UI for discovery and click-to-execute
- **Intent Detection**: AI automatically detects when a skill should be offered

### 2. **Non-Intrusive Assistance**
- Skills are **suggested** when detected, not auto-executed
- User approves before any action (especially for email sending)
- Clear preview of what will happen before execution

### 3. **Transparent & Debuggable**
- Show skill execution steps in chat
- Log all actions for troubleshooting
- Allow users to undo/cancel mid-execution

### 4. **Extensible Architecture**
- Plugin-based system for easy skill addition
- Skills can be enabled/disabled per user preference
- Support for community-contributed skills (future)

---

## Skill Detection & Invocation System

### **Method 1: Intent Detection (AI-Powered)**

**How It Works:**
1. User types natural language query in REPL
2. Before sending to AI provider, run **local intent classifier**
3. If skill intent detected with confidence > 80%, show **skill suggestion card**
4. User can click "Use Skill" or "Continue with Chat"

**Intent Classifier:**
```python
class IntentClassifier:
    """Lightweight local classifier for skill detection."""

    PATTERNS = {
        'email_draft': [
            r'(draft|write|compose|create)\s+(an?\s+)?(email|message)',
            r'send\s+(an?\s+)?email',
            r'email\s+(to|about)',
        ],
        'email_search': [
            r'(find|search|look\s+for)\s+(my\s+)?(email|message)',
            r'show\s+(me\s+)?(emails?|messages?)\s+(from|about|containing)',
            r'when\s+did\s+.*email',
        ],
        'calendar_create': [
            r'(schedule|create|add|set\s+up)\s+(a\s+)?(meeting|appointment|event)',
            r'put.*on\s+(my\s+)?calendar',
        ],
        'file_find': [
            r'(find|locate|search\s+for)\s+(a\s+)?(file|document|folder)',
            r'where\s+is\s+(my|the)',
        ],
        'open_application': [
            r'(open|launch|start|run)\s+\w+',
            r'take\s+me\s+to\s+\w+',
        ],
    }

    def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        """Returns skill intent with confidence score."""
        pass
```

**Example Flow:**
```
User: "Draft an email to Sarah about the Q4 report"
  ↓
[Intent Classifier detects: email_draft, confidence=95%]
  ↓
[Show Suggestion Card]
┌─────────────────────────────────────────────┐
│ 💡 I can help with that!                    │
│                                             │
│ Skill: Email Drafting                      │
│ Action: Create email to Sarah about Q4     │
│                                             │
│ [Use Skill]  [Continue with Chat]          │
└─────────────────────────────────────────────┘
```

---

### **Method 2: Slash Commands (Power Users)**

**Syntax:**
```
/email draft to=sarah@example.com subject="Q4 Report"
/email search from=john about=meeting
/calendar create title="Team Standup" date=tomorrow time=10am
/file find name=budget.xlsx
/open app=outlook
```

**Benefits:**
- Fast, predictable execution
- Autocomplete support
- Parameters clearly defined

---

### **Method 3: GUI Skill Palette**

**UI Component:**
- **Button in toolbar**: "⚡ Skills" opens skill palette
- **Grid of skill cards** with icons and descriptions
- **Click to launch skill wizard** (step-by-step form)

**Skill Palette Example:**
```
┌─────────────────────────────────────────┐
│         ⚡ Available Skills              │
├─────────────────────────────────────────┤
│  📧 Email Drafting                      │
│     Compose emails with AI assistance   │
│     [Launch Wizard]                     │
├─────────────────────────────────────────┤
│  🔍 Email Search                        │
│     Find emails by sender, date, topic  │
│     [Launch Wizard]                     │
├─────────────────────────────────────────┤
│  📅 Calendar Management                 │
│     Schedule meetings and events        │
│     [Launch Wizard]                     │
└─────────────────────────────────────────┘
```

---

## Email Skills (Priority Skills)

### **Skill 1: Email Drafting**

**User Experience:**
```
User: "Draft an email to john@example.com about the project deadline"
  ↓
[Skill Suggestion Card appears]
  ↓
User clicks "Use Skill"
  ↓
[Email Draft Wizard opens]
```

**Email Draft Wizard (Step-by-Step):**

```
┌─────────────────────────────────────────┐
│ Step 1/4: Email Recipients              │
├─────────────────────────────────────────┤
│ To: [john@example.com           ]       │
│ CC: [                           ]       │
│ BCC:[                           ]       │
│                                         │
│         [Back]  [Next]  [Cancel]        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Step 2/4: Subject Line                  │
├─────────────────────────────────────────┤
│ Subject: [Project Deadline Update]      │
│                                         │
│ 💡 AI Suggestion:                       │
│ "Update on Project Timeline"            │
│ [Use Suggestion]                        │
│                                         │
│         [Back]  [Next]  [Cancel]        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Step 3/4: Email Body                    │
├─────────────────────────────────────────┤
│ Tell me what you want to say:           │
│ ┌─────────────────────────────────────┐ │
│ │ I need to inform John that we're   │ │
│ │ pushing the deadline to next week  │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Tone: [●Professional ○Casual ○Formal]  │
│ Length: [●Medium ○Brief ○Detailed]     │
│                                         │
│ [✨ Generate Draft]                     │
│                                         │
│         [Back]  [Next]  [Cancel]        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Step 4/4: Review & Send                 │
├─────────────────────────────────────────┤
│ To: john@example.com                    │
│ Subject: Project Deadline Update        │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Hi John,                            │ │
│ │                                     │ │
│ │ I wanted to update you on the       │ │
│ │ project timeline. After reviewing   │ │
│ │ our progress, we'll need to extend  │ │
│ │ the deadline to next week to ensure │ │
│ │ quality delivery.                   │ │
│ │                                     │ │
│ │ Let me know if you have any         │ │
│ │ questions.                          │ │
│ │                                     │ │
│ │ Best regards                        │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ [📝 Edit] [🔄 Regenerate] [Copy to      │
│           Clipboard] [Open in Email     │
│           Client]                       │
│                                         │
│         [Back]        [Cancel]          │
└─────────────────────────────────────────┘
```

**Backend Flow:**
1. Extract parameters (to, subject, intent) from user input
2. Show wizard with pre-filled fields
3. User refines parameters
4. Call AI with specialized prompt:
   ```
   System: You are an email writing assistant. Generate a professional email.
   To: {recipient}
   Subject: {subject}
   Intent: {user_intent}
   Tone: {tone}
   Length: {length}

   Generate only the email body, no subject line.
   ```
5. Display draft to user with edit/regenerate options
6. **Final action: Create email in Outlook**

**Outlook Integration (Local Only):**
```python
class OutlookEmailDrafter:
    """Create email drafts in Outlook via COM automation."""

    def create_draft(self, to: str, subject: str, body: str,
                    cc: str = None, bcc: str = None) -> bool:
        """
        Create email draft in Outlook client (local only).

        Returns:
            True if draft created successfully
        """
        import win32com.client

        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = MailItem

        mail.To = to
        if cc:
            mail.CC = cc
        if bcc:
            mail.BCC = bcc
        mail.Subject = subject
        mail.Body = body

        # Display draft (doesn't send, user must click Send)
        mail.Display(False)  # False = non-modal window

        return True
```

**Key Points:**
- ✅ Creates draft in Outlook - user reviews before sending
- ✅ No external network calls - all local COM automation
- ✅ Uses existing Outlook signature if configured
- ✅ Preserves Outlook formatting and settings

---

### **Skill 2: Email Search**

**User Experience:**
```
User: "Find emails from John sent last week about the budget"
  ↓
[Skill Suggestion Card]
  ↓
[Email Search Wizard opens]
```

**Email Search Wizard:**

```
┌─────────────────────────────────────────┐
│ 🔍 Email Search                         │
├─────────────────────────────────────────┤
│ Search Filters:                         │
│                                         │
│ From: [john@example.com        ] [×]    │
│ Date Range: [Last 7 days ▼]            │
│ Contains Keywords: [budget     ] [×]    │
│ Has Attachments: [○Yes ●Any ○No]       │
│                                         │
│ [+ Add Filter]                          │
│                                         │
│              [Search]  [Cancel]         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🔍 Search Results (3 found)             │
├─────────────────────────────────────────┤
│ ✉️ Q4 Budget Review                     │
│    From: john@example.com               │
│    Date: Dec 15, 2024                   │
│    Preview: "Here's the updated budget  │
│    spreadsheet for Q4..."               │
│    [Open in Email Client]               │
├─────────────────────────────────────────┤
│ ✉️ Budget Meeting Notes                 │
│    From: john@example.com               │
│    Date: Dec 14, 2024                   │
│    [Open in Email Client]               │
├─────────────────────────────────────────┤
│ ✉️ Re: Budget Approval                  │
│    From: john@example.com               │
│    Date: Dec 13, 2024                   │
│    [Open in Email Client]               │
└─────────────────────────────────────────┘
```

**Email Search Backend:**

**Outlook-Only Integration (Local System)**
```python
class OutlookEmailSearcher:
    """
    Search Outlook emails via win32com COM automation.

    IMPORTANT: Only searches local Outlook client - no external queries.
    All searches are performed against locally cached emails.
    """

    def search(self, filters: EmailSearchFilters) -> List[EmailResult]:
        """
        Search emails using Outlook Object Model.

        Filters:
            - from_address: Email sender
            - date_range: (start_date, end_date) tuple
            - keywords: Search in subject or body
            - has_attachments: True/False/None
            - folder: Inbox, Sent, All (default: Inbox)
        """
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")

        # Get folder (Inbox=6, Sent=5, All Folders=iterate)
        folder = namespace.GetDefaultFolder(filters.get('folder', 6))

        # Build Outlook filter string
        # Examples: "[SenderEmailAddress] = 'john@example.com'"
        #          "[ReceivedTime] >= '12/01/2024'"
        filter_str = self._build_outlook_filter(filters)
        items = folder.Items.Restrict(filter_str)

        return [self._parse_email(item) for item in items]

    def _build_outlook_filter(self, filters: EmailSearchFilters) -> str:
        """
        Build Outlook filter string using DASL syntax.
        Only accesses local Outlook data - no server queries.
        """
        conditions = []

        if filters.get('from_address'):
            conditions.append(f"[SenderEmailAddress] = '{filters['from_address']}'")

        if filters.get('date_range'):
            start, end = filters['date_range']
            conditions.append(f"[ReceivedTime] >= '{start}'")
            conditions.append(f"[ReceivedTime] <= '{end}'")

        if filters.get('keywords'):
            # Search in subject or body
            kw = filters['keywords']
            conditions.append(f"(@SQL=\"urn:schemas:httpmail:subject\" LIKE '%{kw}%' OR "
                            f"\"urn:schemas:httpmail:textdescription\" LIKE '%{kw}%')")

        return " AND ".join(conditions) if conditions else ""
```

**Key Points:**
- ✅ Only searches local Outlook cache - no network queries
- ✅ Fast search using Outlook's built-in indexing
- ✅ Access to Inbox, Sent, Drafts, and all custom folders
- ✅ DASL (DAV Searching and Locating) syntax for complex queries

---

## Additional Desktop Skills

### **Skill 3: Calendar Management**

**Capabilities:**
- Create calendar events in Outlook
- Find available time slots
- List upcoming meetings
- Send meeting invites

**Outlook Calendar Integration (Local Only):**
```python
class OutlookCalendarManager:
    """Manage Outlook calendar via COM automation."""

    def create_event(self, subject: str, start: datetime, end: datetime,
                    location: str = None, body: str = None,
                    attendees: List[str] = None) -> bool:
        """
        Create calendar appointment DRAFT in Outlook (local only).

        IMPORTANT: Only creates draft - does NOT send invites or save automatically.
        User must review and click "Send" or "Save" in Outlook window.
        """
        import win32com.client

        outlook = win32com.client.Dispatch("Outlook.Application")
        appointment = outlook.CreateItem(1)  # 1 = AppointmentItem

        appointment.Subject = subject
        appointment.Start = start
        appointment.End = end

        if location:
            appointment.Location = location
        if body:
            appointment.Body = body
        if attendees:
            for email in attendees:
                appointment.Recipients.Add(email)

        # Display draft (doesn't save/send, user must click Save or Send)
        appointment.Display(False)  # False = non-modal window

        return True

    def get_upcoming_meetings(self, days: int = 7) -> List[dict]:
        """Get upcoming calendar events from Outlook."""
        import win32com.client
        from datetime import datetime, timedelta

        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        calendar = namespace.GetDefaultFolder(9)  # 9 = Calendar

        # Filter for upcoming events
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)

        items = calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")

        filter_str = (f"[Start] >= '{start_date.strftime('%m/%d/%Y')}' AND "
                     f"[Start] <= '{end_date.strftime('%m/%d/%Y')}'")
        restricted = items.Restrict(filter_str)

        return [self._parse_appointment(item) for item in restricted]
```

**Example:**
```
User: "Schedule a team meeting for tomorrow at 2pm"
  ↓
[Calendar Wizard]
  ↓
Creates DRAFT event and displays in Outlook
  ↓
"✅ Event draft created. Review and click 'Send' in Outlook to send invites."
```

**Key Points:**
- ✅ Creates draft appointment - does NOT auto-save or send
- ✅ Opens Outlook window for user review
- ✅ User must click "Send" (for meetings) or "Save" (for appointments)
- ✅ No invites sent without explicit user confirmation

---

### **Skill 4: File & Folder Operations**

**Capabilities:**
- Find files by name, content, or date
- Open files/folders
- Organize files (move, rename)
- Quick access to recent files

**Example:**
```
User: "Find my budget spreadsheet from last month"
  ↓
[File Search]
  ↓
Shows list of matching files
  ↓
User clicks to open in default app
```

**Backend:**
- Windows Search API
- Direct filesystem traversal with indexing
- Recent files from Windows jump lists

---

### **Skill 5: Web Search & Research**

**Capabilities:**
- Perform web searches
- Summarize search results
- Open URLs in browser
- Save web content to notes

**Example:**
```
User: "Search for Python async best practices"
  ↓
[Performs web search]
  ↓
Shows top 5 results with AI-generated summaries
  ↓
User can open links or ask follow-up questions
```

---

### **Skill 6: Application Launcher**

**Capabilities:**
- Open installed applications
- Launch websites
- Run command-line tools
- Create desktop shortcuts

**Example:**
```
User: "/open notepad"
  ↓
Launches Notepad.exe
  ↓
"✅ Opened Notepad"
```

**Backend:**
- Windows Start Menu indexing
- Registry scan for installed apps
- PATH environment variable for CLI tools

---

### **Skill 7: Clipboard Management**

**Capabilities:**
- Copy text/data to clipboard
- Retrieve clipboard history
- Format clipboard content
- Share clipboard across devices (future)

**Example:**
```
User: "Copy that email draft to my clipboard"
  ↓
[Copies to clipboard]
  ↓
"✅ Copied to clipboard. Paste anywhere with Ctrl+V"
```

---

### **Skill 8: System Information**

**Capabilities:**
- Show disk space
- Check network status
- Display running processes
- System health diagnostics

**Example:**
```
User: "How much disk space do I have left?"
  ↓
"C: drive has 124 GB free of 500 GB (24% used)"
```

---

### **Skill 9: Note Taking & Quick Capture**

**Capabilities:**
- Create quick notes
- Save thoughts/ideas
- OCR from screenshots
- Voice-to-text notes

**Example:**
```
User: "Save this idea: Use RAG for email context"
  ↓
Creates note with timestamp
  ↓
"✅ Note saved to Quick Notes"
```

---

### **Skill 10: Excel/Spreadsheet Operations**

**Capabilities:**
- Create spreadsheets from data in chat
- Read and query Excel files
- Add/modify data in existing spreadsheets
- Calculate formulas (sum, average, etc.)
- Export conversation data to Excel

**Example:**
```
User: "Create a spreadsheet with these sales figures"
  ↓
[Wizard collects data]
  ↓
Creates Excel file and opens it
  ↓
"✅ Created sales_report.xlsx"
```

**Integration:**
- `openpyxl` for reading/writing .xlsx files
- `pandas` for data manipulation
- COM automation to open in Excel

---

### **Skill 11: Document Management & OCR**

**Capabilities:**
- Summarize PDF documents
- Extract text from images (OCR)
- Convert documents between formats
- Merge/split PDFs
- Extract tables from documents

**Example:**
```
User: "Summarize this contract PDF"
  ↓
[Reads PDF, generates summary]
  ↓
Shows key points and terms
```

**Tools:**
- `pypdf` for PDF operations
- `pytesseract` for OCR
- `PIL` (Pillow) for image processing
- Existing RAG pipeline for document analysis

---

### **Skill 12: Smart Folder Organization**

**Capabilities:**
- Organize files by type, date, or content
- Move files based on rules
- Clean up duplicate files
- Archive old files
- Batch rename files

**Example:**
```
User: "Organize my downloads folder by file type"
  ↓
[Scans Downloads, creates subfolders]
  ↓
"✅ Organized 47 files into 5 categories"
```

**Safety:**
- Preview changes before executing
- Undo capability (tracks moves)
- Never delete without confirmation

---

### **Skill 13: Meeting Preparation Assistant**

**Capabilities:**
- Prepare meeting agendas from emails/context
- Summarize action items from meeting notes
- Find all related emails for meeting context
- Create meeting notes templates
- Extract attendees from email threads

**Example:**
```
User: "Prepare for my 2pm meeting with John"
  ↓
[Searches emails from John, calendar details]
  ↓
Shows agenda with context and recent emails
```

**Integration:**
- Outlook email search
- Outlook calendar integration
- RAG for context extraction

---

### **Skill 14: Teams/Chat Quick Messages**

**Capabilities:**
- Draft professional chat messages
- Send status updates
- Format messages (code blocks, lists)
- Set presence status

**Example:**
```
User: "Send a status update to my team"
  ↓
[Wizard: What's the update?]
  ↓
Generates professional message
  ↓
[Copy to Clipboard] or [Open Teams]
```

**Note:** No direct Teams API integration (no external queries) - generates formatted message for user to copy

---

### **Skill 15: Window & Workspace Management**

**Capabilities:**
- Arrange windows (side-by-side, grid)
- Save workspace layouts
- Open "work setup" (specific apps + positions)
- Manage virtual desktops

**Example:**
```
User: "Set up my coding workspace"
  ↓
Opens VS Code, terminal, browser in configured layout
  ↓
"✅ Workspace ready"
```

**Windows APIs:**
- `win32gui` for window manipulation
- `pygetwindow` for window enumeration
- Windows Virtual Desktop API

---

### **Skill 16: System Maintenance**

**Capabilities:**
- Clean temporary files
- Check disk space by folder
- Find large files
- Monitor system health
- Check for Windows updates

**Example:**
```
User: "Clean up temporary files"
  ↓
[Scans temp folders, shows space to free]
  ↓
User confirms
  ↓
"✅ Freed 2.3 GB of disk space"
```

**Safety:**
- Only touches known safe temp locations
- Shows preview before deletion
- Never touches user data without confirmation

---

### **Skill 17: Security & Backup Helper**

**Capabilities:**
- Backup folders to destination
- Check Windows Update status
- Verify file integrity (checksums)
- Show recent login attempts
- Monitor firewall status

**Example:**
```
User: "Backup my Documents folder"
  ↓
[Wizard: Where to backup?]
  ↓
Copies files with progress
  ↓
"✅ Backed up 1,234 files (4.2 GB)"
```

**Safety:**
- Read-only scans for security info
- Backups are copies, never moves
- User chooses destination

---

### **Skill 18: Task & Reminder Management**

**Capabilities:**
- Create reminders with Windows Task Scheduler
- Add tasks to Outlook Tasks
- List today's tasks
- Mark tasks complete
- Recurring reminders

**Example:**
```
User: "Remind me to call John tomorrow at 2pm"
  ↓
Creates Outlook task with reminder
  ↓
"✅ Reminder set for Dec 20, 2024 at 2:00 PM"
```

**Integration:**
- Outlook Tasks (COM API)
- Windows Task Scheduler (for system-level reminders)

---

### **Skill 19: Bookmark & Link Management**

**Capabilities:**
- Save URLs with notes
- Organize bookmarks by category
- Search saved links
- Export/import browser bookmarks

**Example:**
```
User: "Save this article for later: python.org/docs"
  ↓
[Wizard: Add tags/notes?]
  ↓
"✅ Saved to Bookmarks > Python > Documentation"
```

**Storage:**
- Local SQLite database
- Optional browser bookmark export

---

### **Skill 20: Screenshot & Screen Capture**

**Capabilities:**
- Take screenshots (full screen, window, region)
- OCR text from screenshots
- Annotate screenshots
- Save to clipboard or file

**Example:**
```
User: "Screenshot this window and extract the text"
  ↓
[Captures active window, runs OCR]
  ↓
Shows extracted text + saves image
```

**Tools:**
- `PIL` for capturing
- `pytesseract` for OCR
- Windows Snipping Tool API (optional)

---

### **Skill 21: Network Utilities**

**Capabilities:**
- Show IP address (local & public)
- Test connection (ping)
- Show active network connections
- Display network adapters
- Check internet speed (estimate)

**Example:**
```
User: "What's my IP address?"
  ↓
"Local: 192.168.1.42
 Public: 203.0.113.45"
```

**Tools:**
- `socket` for network info
- `requests` for public IP (single query to ifconfig.me)
- `subprocess` for ping

---

### **Skill 22: Text Formatting & Templates**

**Capabilities:**
- Format text as letter, memo, invoice
- Apply consistent styling
- Create templates
- Proofread and suggest improvements
- Generate professional bios/intros

**Example:**
```
User: "Format this as a formal business letter"
  ↓
[Applies letterhead, date, formatting]
  ↓
Shows formatted version
```

**Integration:**
- AI for content generation
- Templates stored locally

---

### **Skill 23: Batch Image Operations**

**Capabilities:**
- Resize images (single or batch)
- Convert formats (JPG, PNG, etc.)
- Compress images
- Add watermarks
- Rename by EXIF date

**Example:**
```
User: "Resize these vacation photos to 1920x1080"
  ↓
[Processes batch with progress]
  ↓
"✅ Resized 43 images"
```

**Tools:**
- `PIL` (Pillow) for image operations
- `piexif` for EXIF data

---

### **Skill 24: Personal Knowledge Base**

**Capabilities:**
- Save information to local wiki
- Tag and categorize notes
- Search knowledge base
- Link related notes
- Export to markdown

**Example:**
```
User: "Save this: React hooks use state for local data"
  ↓
[Wizard: Tags?]
  ↓
"✅ Saved to Knowledge Base > React > Hooks"
```

**Storage:**
- Local SQLite database
- Markdown export option
- Integration with existing RAG for search

---

### **Skill 25: Cross-App Smart Search**

**Capabilities:**
- Search across Outlook, Files, Notes in one query
- Timeline view of all activity
- Find all mentions of topic/person

**Example:**
```
User: "Find everything about the Q4 budget"
  ↓
Searches emails, files, notes, calendar
  ↓
Shows unified results with dates
```

**Integration:**
- Outlook search (emails, calendar)
- Windows Search API (files)
- Knowledge base search

---

### **Skill 26: Report Generation**

**Capabilities:**
- Weekly summary reports
- Email volume statistics
- Time tracking summaries
- Activity reports

**Example:**
```
User: "Generate my weekly email summary"
  ↓
[Analyzes emails from past week]
  ↓
Shows stats: sent, received, top senders, etc.
```

**Data Sources:**
- Outlook emails
- Calendar events
- File modifications
- Local activity logs

---

### **Skill 27: Text-to-Speech Reader**

**Capabilities:**
- Read documents aloud
- Read emails aloud
- Adjustable speed and voice
- Background reading mode

**Example:**
```
User: "Read this PDF to me"
  ↓
[Converts PDF to text, starts TTS]
  ↓
Plays audio with pause/resume controls
```

**Windows Integration:**
- Windows Speech API (SAPI)
- `pyttsx3` for cross-platform TTS

---

### **Skill 28: Environment & Focus Modes**

**Capabilities:**
- Toggle dark mode
- Enable night light
- Mute notifications for duration
- Set focus mode (DND)
- Adjust screen brightness

**Example:**
```
User: "Enable focus mode for 1 hour"
  ↓
Mutes notifications, sets status
  ↓
"✅ Focus mode active until 3:45 PM"
```

**Windows APIs:**
- Focus Assist API
- Display settings
- Notification settings

---

### **Skill 29: Simple Workflow Automation**

**Capabilities:**
- Auto-save email attachments to folder
- Daily digest of unread emails
- Auto-organize downloads
- Scheduled file backups

**Example:**
```
User: "Save all PDF attachments from John to My Documents"
  ↓
[Sets up rule]
  ↓
"✅ Rule active. PDFs from John will auto-save."
```

**Implementation:**
- Outlook rules (for email automation)
- Windows Task Scheduler (for scheduled tasks)
- File system watcher for folder monitoring

---

### **Skill 30: Expense Tracking**

**Capabilities:**
- Log expenses with date/amount/category
- Monthly spending reports
- Export to Excel
- Parse receipts (OCR)

**Example:**
```
User: "Log expense: $45 for lunch"
  ↓
[Saves to local database]
  ↓
"✅ Logged: $45 - Food - Dec 19, 2024"
```

**Storage:**
- Local SQLite database
- No cloud sync (privacy)
- Export to Excel for analysis

---

## Technical Architecture

### **Directory Structure**

```
specter/src/
├── infrastructure/
│   └── skills/
│       ├── __init__.py
│       ├── skill_manager.py          # Central skill orchestrator
│       ├── intent_classifier.py      # Detects user intent
│       ├── skill_registry.py         # Plugin registration
│       ├── base_skill.py             # Abstract base class
│       │
│       ├── email/
│       │   ├── __init__.py
│       │   ├── email_draft_skill.py
│       │   ├── email_search_skill.py
│       │   ├── outlook_connector.py  # COM automation
│       │   ├── imap_connector.py     # IMAP protocol
│       │   └── gmail_connector.py    # Gmail API (future)
│       │
│       ├── calendar/
│       │   ├── __init__.py
│       │   ├── calendar_create_skill.py
│       │   └── outlook_calendar.py
│       │
│       ├── file_operations/
│       │   ├── __init__.py
│       │   ├── file_search_skill.py
│       │   └── windows_search.py
│       │
│       └── web/
│           ├── __init__.py
│           └── web_search_skill.py
│
└── presentation/
    └── widgets/
        ├── skill_suggestion_card.py   # Intent suggestion UI
        ├── skill_palette_widget.py    # Skill browser
        └── wizards/
            ├── email_draft_wizard.py
            └── email_search_wizard.py
```

---

### **Core Components**

#### **1. Skill Manager**
```python
class SkillManager:
    """Central orchestrator for all skills."""

    def __init__(self):
        self.registry = SkillRegistry()
        self.intent_classifier = IntentClassifier()
        self._enabled_skills = set()

    def register_skill(self, skill: BaseSkill):
        """Register a new skill plugin."""
        self.registry.add(skill)
        if skill.enabled_by_default:
            self._enabled_skills.add(skill.skill_id)

    def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        """Detect if user input matches a skill."""
        return self.intent_classifier.detect_intent(user_input)

    def execute_skill(self, skill_id: str, params: dict) -> SkillResult:
        """Execute a skill with given parameters."""
        skill = self.registry.get(skill_id)
        return skill.execute(params)
```

#### **2. Base Skill Class**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class SkillMetadata:
    """Metadata describing a skill."""
    skill_id: str
    name: str
    description: str
    category: str  # email, calendar, file, web, system
    icon: str  # emoji or path to icon
    enabled_by_default: bool = True
    requires_confirmation: bool = True  # Ask before executing


@dataclass
class SkillParameter:
    """A parameter that the skill needs."""
    name: str
    type: type  # str, int, bool, datetime, etc.
    required: bool
    description: str
    default: Any = None


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseSkill(ABC):
    """Base class for all skills."""

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute the skill with given parameters."""
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate that required parameters are present."""
        for param in self.parameters:
            if param.required and param.name not in params:
                return False
        return True
```

#### **3. Email Draft Skill Implementation**
```python
class EmailDraftSkill(BaseSkill):
    """Skill for drafting emails with AI assistance."""

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            skill_id="email_draft",
            name="Email Drafting",
            description="Compose professional emails with AI assistance",
            category="email",
            icon="📧",
            requires_confirmation=True
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter("to", str, required=True, description="Recipient email"),
            SkillParameter("subject", str, required=False, description="Email subject"),
            SkillParameter("intent", str, required=True, description="What you want to say"),
            SkillParameter("tone", str, required=False, default="professional",
                         description="Email tone: professional, casual, formal"),
            SkillParameter("length", str, required=False, default="medium",
                         description="Email length: brief, medium, detailed"),
        ]

    def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Generate email draft using AI."""
        if not self.validate_params(params):
            return SkillResult(
                success=False,
                message="Missing required parameters",
                error="'to' and 'intent' are required"
            )

        # Generate email using AI
        draft = self._generate_draft(
            to=params['to'],
            subject=params.get('subject', ''),
            intent=params['intent'],
            tone=params.get('tone', 'professional'),
            length=params.get('length', 'medium')
        )

        return SkillResult(
            success=True,
            message="Email draft generated",
            data={
                'draft': draft,
                'to': params['to'],
                'subject': params.get('subject', ''),
            }
        )

    def _generate_draft(self, to: str, subject: str, intent: str,
                       tone: str, length: str) -> str:
        """Call AI service to generate email body."""
        from ...ai.ai_service import AIService

        prompt = f"""Generate a {tone} email body. Do not include subject line or signature.

To: {to}
Intent: {intent}
Tone: {tone}
Length: {length}

Email body only:"""

        # Use existing AI service
        ai_service = AIService()
        response = ai_service.generate_completion(prompt)
        return response
```

---

### **4. Intent Detection System**

**Hybrid Approach (Fast & Accurate):**

1. **Local Pattern Matching** (instant, 0ms latency)
   - Regex patterns for common intents
   - Keyword matching
   - 80% accuracy, covers most cases

2. **AI-Powered Classification** (optional, 200-500ms)
   - Use LLM for ambiguous cases
   - Only when local matching is uncertain
   - Higher accuracy for complex queries

```python
class IntentClassifier:
    """Detects user intent to trigger skills."""

    def detect_intent(self, user_input: str) -> Optional[SkillIntent]:
        """
        Detect intent using hybrid approach.

        Returns:
            SkillIntent with skill_id, confidence, and extracted params
        """
        # Step 1: Local pattern matching
        local_match = self._local_pattern_match(user_input)

        if local_match and local_match.confidence > 0.85:
            # High confidence from local matching
            return local_match

        # Step 2: AI classification (optional, user setting)
        if self._ai_classification_enabled():
            ai_match = self._ai_classify(user_input)
            if ai_match and ai_match.confidence > local_match.confidence:
                return ai_match

        # Step 3: Return local match if above threshold
        if local_match and local_match.confidence > 0.65:
            return local_match

        return None

    def _local_pattern_match(self, text: str) -> Optional[SkillIntent]:
        """Fast regex-based pattern matching."""
        text_lower = text.lower()

        # Email drafting patterns
        if any(re.search(p, text_lower) for p in self.PATTERNS['email_draft']):
            params = self._extract_email_params(text)
            return SkillIntent(
                skill_id='email_draft',
                confidence=0.90,
                extracted_params=params
            )

        # Email search patterns
        if any(re.search(p, text_lower) for p in self.PATTERNS['email_search']):
            params = self._extract_search_params(text)
            return SkillIntent(
                skill_id='email_search',
                confidence=0.85,
                extracted_params=params
            )

        # ... more patterns

        return None

    def _extract_email_params(self, text: str) -> dict:
        """Extract email parameters from natural language."""
        params = {}

        # Extract recipient
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            params['to'] = emails[0]

        # Extract name (if email not explicit)
        name_pattern = r'to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        names = re.findall(name_pattern, text)
        if names and 'to' not in params:
            params['to_name'] = names[0]

        # Extract subject/intent
        about_pattern = r'about\s+(.+?)(?:\.|$)'
        about_match = re.search(about_pattern, text)
        if about_match:
            params['intent'] = about_match.group(1).strip()

        return params
```

---

### **5. User Interface Components**

#### **Skill Suggestion Card**
```python
class SkillSuggestionCard(QFrame):
    """
    Card that appears when a skill is detected.
    Non-intrusive, dismissable, clear call-to-action.
    """

    skill_accepted = pyqtSignal(str, dict)  # skill_id, params
    skill_rejected = pyqtSignal()

    def __init__(self, intent: SkillIntent, parent=None):
        super().__init__(parent)
        self.intent = intent
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("💡 I can help with that!")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        # Skill description
        skill_name = self.intent.skill_metadata.name
        action_desc = self._generate_action_description()

        desc_label = QLabel(f"<b>Skill:</b> {skill_name}<br>"
                           f"<b>Action:</b> {action_desc}")
        layout.addWidget(desc_label)

        # Buttons
        btn_layout = QHBoxLayout()

        use_btn = QPushButton("Use Skill")
        use_btn.clicked.connect(self._on_use_skill)
        btn_layout.addWidget(use_btn)

        chat_btn = QPushButton("Continue with Chat")
        chat_btn.clicked.connect(self._on_reject)
        btn_layout.addWidget(chat_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # Styling
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 144, 255, 0.1);
                border-left: 3px solid #1E90FF;
                border-radius: 4px;
                padding: 12px;
            }
        """)
```

#### **Skill Palette Widget**
```python
class SkillPaletteWidget(QWidget):
    """
    Grid of available skills for discovery.
    Appears when user clicks "⚡ Skills" button.
    """

    skill_selected = pyqtSignal(str)  # skill_id

    def __init__(self, skill_manager: SkillManager, parent=None):
        super().__init__(parent)
        self.skill_manager = skill_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("⚡ Available Skills")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Search bar
        search = QLineEdit()
        search.setPlaceholderText("Search skills...")
        search.textChanged.connect(self._filter_skills)
        layout.addWidget(search)

        # Skill grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        grid_widget = QWidget()
        grid_layout = QGridLayout()

        # Populate skills
        skills = self.skill_manager.registry.get_all()
        row, col = 0, 0
        for skill in skills:
            card = self._create_skill_card(skill)
            grid_layout.addWidget(card, row, col)

            col += 1
            if col >= 2:  # 2 columns
                col = 0
                row += 1

        grid_widget.setLayout(grid_layout)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        self.setLayout(layout)
```

---

## Integration with Existing REPL

### **1. Add Skill Manager to REPL**

```python
# In repl_widget.py __init__

from ...infrastructure.skills.skill_manager import SkillManager

class REPLWidget(QWidget):
    def __init__(self):
        # ... existing code ...

        # Initialize skill system
        self.skill_manager = SkillManager()
        self._register_default_skills()

        # Connect signals
        self.command_input.textChanged.connect(self._on_input_changed)
```

### **2. Intent Detection on User Input**

```python
def _on_input_changed(self):
    """Detect skills as user types (debounced)."""
    user_input = self.command_input.toPlainText()

    # Debounce (wait 500ms after user stops typing)
    if hasattr(self, '_intent_timer'):
        self._intent_timer.stop()

    self._intent_timer = QTimer()
    self._intent_timer.setSingleShot(True)
    self._intent_timer.timeout.connect(
        lambda: self._check_for_skill_intent(user_input)
    )
    self._intent_timer.start(500)

def _check_for_skill_intent(self, user_input: str):
    """Check if input matches any skill intent."""
    intent = self.skill_manager.detect_intent(user_input)

    if intent and intent.confidence > 0.75:
        # Show skill suggestion card
        self._show_skill_suggestion(intent)
```

### **3. Skill Suggestion UI**

```python
def _show_skill_suggestion(self, intent: SkillIntent):
    """Display skill suggestion card above input."""
    # Remove existing suggestion if any
    if hasattr(self, '_skill_card') and self._skill_card:
        self._skill_card.deleteLater()

    # Create new suggestion card
    self._skill_card = SkillSuggestionCard(intent)
    self._skill_card.skill_accepted.connect(self._launch_skill_wizard)
    self._skill_card.skill_rejected.connect(self._hide_skill_suggestion)

    # Insert above input area
    self.layout().insertWidget(
        self.layout().indexOf(self.command_input),
        self._skill_card
    )
```

---

## Settings & Configuration

### **Skill Settings Page**

```
┌─────────────────────────────────────────┐
│ ⚡ Skills Configuration                 │
├─────────────────────────────────────────┤
│                                         │
│ Skill Detection:                        │
│   [✓] Enable automatic skill detection  │
│   [✓] Show skill suggestions            │
│   [ ] Use AI for intent classification  │
│       (slower but more accurate)        │
│                                         │
│ Enabled Skills:                         │
│   [✓] Email Drafting                    │
│   [✓] Email Search                      │
│   [✓] Calendar Management               │
│   [✓] File Search                       │
│   [ ] Web Search (experimental)         │
│   [✓] Application Launcher              │
│                                         │
│ Email Configuration:                    │
│   Email Client: [Outlook Desktop ▼]    │
│   Default From: [user@example.com  ]    │
│   Signature: [Use default      ▼]      │
│                                         │
│ Advanced:                               │
│   Skill Confidence Threshold: [75%]     │
│   (Higher = fewer false positives)      │
│                                         │
│              [Save]  [Reset to Default] │
└─────────────────────────────────────────┘
```

**Settings Schema:**
```json
{
  "skills": {
    "enabled": true,
    "show_suggestions": true,
    "use_ai_classification": false,
    "confidence_threshold": 0.75,
    "enabled_skills": [
      "email_draft",
      "email_search",
      "calendar_create",
      "file_search",
      "app_launcher"
    ],
    "email": {
      "client": "outlook_desktop",
      "default_from": "user@example.com",
      "signature": "default"
    }
  }
}
```

---

## Error Handling & User Feedback

### **Graceful Degradation**

1. **Email client not available:**
   ```
   ⚠️ Outlook is not installed.

   I've copied the email draft to your clipboard.
   You can paste it into any email client.

   [Copy Again]  [Install Outlook]  [Configure Different Client]
   ```

2. **Skill execution failed:**
   ```
   ❌ Failed to search emails.

   Error: Could not connect to mail server.

   Troubleshooting:
   • Check your internet connection
   • Verify email client is running
   • Check settings: [Open Email Settings]

   [Try Again]  [Report Issue]
   ```

3. **Ambiguous intent:**
   ```
   🤔 I'm not sure which skill to use.

   Did you want to:
   • Draft a new email
   • Search existing emails
   • Continue with regular chat

   [Draft Email]  [Search Emails]  [Chat]
   ```

---

## Privacy & Security

### **Data Handling Principles**

1. **Local-First Processing**
   - Intent detection runs locally (no API calls)
   - Email content never sent to AI unless user explicitly generates draft
   - Search operates on local email database/cache

2. **User Consent**
   - Skills require confirmation before executing actions
   - Clear preview of what will happen
   - Undo capability where possible

3. **Credential Management**
   - Email passwords stored in Windows Credential Manager
   - OAuth tokens encrypted at rest
   - No plaintext password storage

4. **Logging**
   - Skill executions logged for debugging
   - PII (email addresses, names) redacted in logs
   - Option to disable skill logging

---

## Future Enhancements

### **Phase 2 Skills (Post-MVP)**

1. **Document Generation**
   - Create Word/PDF documents
   - Fill templates
   - Export chat to document

2. **Meeting Assistant**
   - Join Zoom/Teams meetings
   - Transcribe meetings
   - Generate meeting summaries

3. **Code Execution**
   - Run Python/JavaScript snippets
   - Execute shell commands
   - Git operations

4. **Automation Workflows**
   - Chain multiple skills
   - Conditional logic
   - Scheduled execution

5. **Custom Skills**
   - User-defined skill templates
   - JavaScript/Python plugin API
   - Community skill marketplace

### **Advanced Features**

1. **Context Awareness**
   - Skills remember previous executions
   - Learn user preferences
   - Suggest skills based on usage patterns

2. **Multi-Step Skills**
   - Wizard-like flows
   - Decision trees
   - Error recovery

3. **Collaboration**
   - Share skills with team
   - Approve skill executions for others
   - Audit logs

---

## Success Metrics

### **User Adoption**
- % of users who enable skills
- % of queries that trigger skills
- Skill acceptance rate (use vs. dismiss)

### **Usability**
- Time to complete task (with skill vs. manual)
- Error rate
- User satisfaction scores

### **Technical**
- Intent detection accuracy
- Skill execution success rate
- Average latency

---

## Implementation Roadmap

### **Phase 1: Foundation (Week 1-2)**
- [ ] Create skill infrastructure
- [ ] Implement SkillManager and BaseSkill
- [ ] Build intent detection system
- [ ] Add skill settings page

### **Phase 2: Email Skills (Week 3-4)**
- [ ] Email Draft Skill + Wizard
- [ ] Email Search Skill + UI
- [ ] Outlook COM integration
- [ ] IMAP fallback

### **Phase 3: UI/UX (Week 5)**
- [ ] Skill suggestion cards
- [ ] Skill palette widget
- [ ] Integrate with REPL
- [ ] Polish animations/transitions

### **Phase 4: Additional Skills (Week 6-7)**
- [ ] Calendar management
- [ ] File search
- [ ] Application launcher
- [ ] Web search

### **Phase 5: Testing & Polish (Week 8)**
- [ ] End-to-end testing
- [ ] Error handling
- [ ] Performance optimization
- [ ] Documentation

---

## Open Questions for User

1. **Email Client Priority:**
   - Focus on Outlook first (most common in enterprise)?
   - Or build IMAP/Gmail first (cross-platform)?

2. **Skill Invocation Preference:**
   - Automatic suggestions (proactive)?
   - Manual activation only (user-initiated)?
   - Hybrid (suggestions that can be disabled)?

3. **Email Search Scope:**
   - Search local cache only (fast, private)?
   - Query email server (comprehensive, requires connection)?
   - Both with user preference?

4. **Draft Generation:**
   - Show wizard for all parameters?
   - Or extract as much as possible from natural language?

5. **Security:**
   - Store email credentials locally?
   - Or require OAuth flow for each session?

---

## End of Plan

This architecture provides a **solid foundation** for building user-friendly desktop automation skills. The system is:

✅ **User-friendly** - Multiple invocation methods (NL, slash commands, GUI)
✅ **Safe** - Requires confirmation, clear previews
✅ **Extensible** - Plugin architecture for new skills
✅ **Privacy-first** - Local processing, minimal data sharing
✅ **Non-technical friendly** - Wizards, clear UI, helpful errors

Next step: Get user feedback on priorities and begin implementation!
