"""
Export service for conversation data.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..models.conversation import Conversation
from ..models.enums import ExportFormat, MessageRole
from ..repositories.conversation_repository import ConversationRepository

logger = logging.getLogger("ghostman.export_service")


class ExportService:
    """Service for exporting conversation data to various formats."""
    
    def __init__(self, repository: Optional[ConversationRepository] = None):
        """Initialize export service."""
        self.repository = repository
    
    async def export_conversation(
        self,
        conversation_or_id,  # Can be Conversation object or ID string
        file_path: str,
        format: str,
        include_metadata: bool = True
    ) -> bool:
        """Export a single conversation to file."""
        try:
            # Handle both conversation object and ID
            if isinstance(conversation_or_id, str):
                # It's an ID, load from repository
                if not self.repository:
                    logger.error("Repository required for conversation ID")
                    return False
                conversation = await self.repository.get_conversation(conversation_or_id, include_messages=True)
                if not conversation:
                    logger.error(f"Conversation not found: {conversation_or_id}")
                    return False
            else:
                # It's already a conversation object
                conversation = conversation_or_id
            
            # Export based on format - normalize format string
            format_map = {
                'markdown': 'md',
                'md': 'md',
                'txt': 'txt',
                'text': 'txt',
                'json': 'json',
                'html': 'html'
            }
            normalized_format = format_map.get(format.lower(), format.lower())
            export_format = ExportFormat(normalized_format)
            
            if export_format == ExportFormat.JSON:
                return await self._export_json([conversation], file_path, include_metadata)
            elif export_format == ExportFormat.TXT:
                return await self._export_txt([conversation], file_path, include_metadata)
            elif export_format == ExportFormat.MARKDOWN:
                return await self._export_markdown([conversation], file_path, include_metadata)
            elif export_format == ExportFormat.HTML:
                return await self._export_html([conversation], file_path, include_metadata)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            conv_id = conversation_or_id if isinstance(conversation_or_id, str) else conversation.id
            logger.error(f"❌ Export failed for {conv_id}: {e}")
            return False
    
    async def export_conversations(
        self,
        conversation_ids: List[str],
        format: str,
        file_path: str,
        include_metadata: bool = True
    ) -> bool:
        """Export multiple conversations to file."""
        try:
            # Load conversations
            conversations = []
            for conv_id in conversation_ids:
                conversation = await self.repository.get_conversation(conv_id, include_messages=True)
                if conversation:
                    conversations.append(conversation)
                else:
                    logger.warning(f"Conversation not found, skipping: {conv_id}")
            
            if not conversations:
                logger.error("No conversations found to export")
                return False
            
            # Export based on format - normalize format string
            format_map = {
                'markdown': 'md',
                'md': 'md',
                'txt': 'txt',
                'text': 'txt',
                'json': 'json',
                'html': 'html'
            }
            normalized_format = format_map.get(format.lower(), format.lower())
            export_format = ExportFormat(normalized_format)
            
            if export_format == ExportFormat.JSON:
                return await self._export_json(conversations, file_path, include_metadata)
            elif export_format == ExportFormat.TXT:
                return await self._export_txt(conversations, file_path, include_metadata)
            elif export_format == ExportFormat.MARKDOWN:
                return await self._export_markdown(conversations, file_path, include_metadata)
            elif export_format == ExportFormat.HTML:
                return await self._export_html(conversations, file_path, include_metadata)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Bulk export failed: {e}")
            return False
    
    async def _export_json(
        self,
        conversations: List[Conversation],
        file_path: str,
        include_metadata: bool
    ) -> bool:
        """Export conversations to JSON format."""
        try:
            export_data = {
                'export_info': {
                    'format': 'json',
                    'version': '1.0',
                    'exported_at': datetime.now().isoformat(),
                    'conversation_count': len(conversations),
                    'include_metadata': include_metadata
                },
                'conversations': []
            }
            
            for conversation in conversations:
                conv_data = conversation.to_dict(include_messages=True)
                
                # Remove sensitive metadata if requested
                if not include_metadata:
                    conv_data.pop('metadata', None)
                    for message in conv_data.get('messages', []):
                        message.pop('metadata', None)
                
                export_data['conversations'].append(conv_data)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Exported {len(conversations)} conversations to JSON: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ JSON export failed: {e}")
            return False
    
    async def _export_txt(
        self,
        conversations: List[Conversation],
        file_path: str,
        include_metadata: bool
    ) -> bool:
        """Export conversations to plain text format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"Ghostman Conversation Export\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Conversations: {len(conversations)}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, conversation in enumerate(conversations, 1):
                    # Conversation header
                    f.write(f"CONVERSATION {i}: {conversation.title}\n")
                    f.write(f"Status: {conversation.status.value.title()}\n")
                    f.write(f"Created: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Updated: {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Messages: {len(conversation.messages)}\n")
                    
                    # Metadata
                    if include_metadata and conversation.metadata:
                        if conversation.metadata.tags:
                            f.write(f"Tags: {', '.join(conversation.metadata.tags)}\n")
                        if conversation.metadata.category:
                            f.write(f"Category: {conversation.metadata.category}\n")
                    
                    # Summary
                    if conversation.summary:
                        f.write(f"Summary: {conversation.summary.summary}\n")
                    
                    f.write("-" * 40 + "\n")
                    
                    # Messages
                    for message in conversation.messages:
                        role = message.role.value.upper()
                        timestamp = message.timestamp.strftime('%H:%M:%S')
                        
                        if message.role == MessageRole.SYSTEM:
                            f.write(f"[{timestamp}] SYSTEM: {message.content}\n")
                        elif message.role == MessageRole.USER:
                            f.write(f"[{timestamp}] USER: {message.content}\n")
                        else:  # ASSISTANT
                            f.write(f"[{timestamp}] ASSISTANT: {message.content}\n")
                        f.write("\n")
                    
                    f.write("=" * 80 + "\n\n")
            
            logger.info(f"✅ Exported {len(conversations)} conversations to TXT: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ TXT export failed: {e}")
            return False
    
    async def _export_markdown(
        self,
        conversations: List[Conversation],
        file_path: str,
        include_metadata: bool
    ) -> bool:
        """Export conversations to Markdown format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write("# Ghostman Conversation Export\n\n")
                f.write(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Conversations:** {len(conversations)}\n\n")
                f.write("---\n\n")
                
                for i, conversation in enumerate(conversations, 1):
                    # Conversation header
                    f.write(f"## {i}. {conversation.title}\n\n")
                    
                    # Metadata table
                    f.write("| Property | Value |\n")
                    f.write("|----------|-------|\n")
                    f.write(f"| Status | {conversation.status.value.title()} |\n")
                    f.write(f"| Created | {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')} |\n")
                    f.write(f"| Updated | {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')} |\n")
                    f.write(f"| Messages | {len(conversation.messages)} |\n")
                    
                    if include_metadata and conversation.metadata:
                        if conversation.metadata.tags:
                            tags_str = ", ".join(f"`{tag}`" for tag in conversation.metadata.tags)
                            f.write(f"| Tags | {tags_str} |\n")
                        if conversation.metadata.category:
                            f.write(f"| Category | {conversation.metadata.category} |\n")
                    
                    f.write("\n")
                    
                    # Summary
                    if conversation.summary:
                        f.write("### Summary\n\n")
                        f.write(f"{conversation.summary.summary}\n\n")
                        if conversation.summary.key_topics:
                            f.write("**Key Topics:** ")
                            f.write(", ".join(f"`{topic}`" for topic in conversation.summary.key_topics))
                            f.write("\n\n")
                    
                    # Messages
                    f.write("### Messages\n\n")
                    
                    for message in conversation.messages:
                        timestamp = message.timestamp.strftime('%H:%M:%S')
                        
                        if message.role == MessageRole.SYSTEM:
                            f.write(f"**🔧 SYSTEM** `{timestamp}`\n\n")
                            f.write(f"> {message.content}\n\n")
                        elif message.role == MessageRole.USER:
                            f.write(f"**👤 USER** `{timestamp}`\n\n")
                            f.write(f"{message.content}\n\n")
                        else:  # ASSISTANT
                            f.write(f"**🤖 ASSISTANT** `{timestamp}`\n\n")
                            f.write(f"{message.content}\n\n")
                    
                    f.write("---\n\n")
            
            logger.info(f"✅ Exported {len(conversations)} conversations to Markdown: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Markdown export failed: {e}")
            return False
    
    async def _export_html(
        self,
        conversations: List[Conversation],
        file_path: str,
        include_metadata: bool
    ) -> bool:
        """Export conversations to HTML format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write HTML header (escape braces for CSS)
                html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ghostman Conversation Export</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #444; margin-top: 40px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #007bff; }}
        .metadata {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metadata table {{ width: 100%; border-collapse: collapse; }}
        .metadata td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
        .metadata td:first-child {{ font-weight: bold; width: 150px; }}
        .message {{ margin: 20px 0; padding: 15px; border-radius: 5px; position: relative; }}
        .system {{ background: #e9ecef; border-left: 4px solid #6c757d; }}
        .user {{ background: #e7f3ff; border-left: 4px solid #007bff; }}
        .assistant {{ background: #e8f5e8; border-left: 4px solid #28a745; }}
        .message-header {{ font-weight: bold; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .timestamp {{ font-size: 0.9em; color: #666; }}
        .content {{ white-space: pre-wrap; line-height: 1.6; }}
        .content h1, .content h2, .content h3 {{ margin: 15px 0 10px 0; color: #333; }}
        .content code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
        .content pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        .content pre code {{ background: none; padding: 0; }}
        .content blockquote {{ border-left: 4px solid #ddd; margin: 10px 0; padding-left: 15px; color: #666; }}
        .content ul, .content ol {{ margin: 10px 0; padding-left: 30px; }}
        .content strong {{ font-weight: 600; color: #000; }}
        .content em {{ font-style: italic; }}
        .content a {{ color: #007bff; text-decoration: none; }}
        .content a:hover {{ text-decoration: underline; }}
        .summary {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        .tags {{ margin: 10px 0; }}
        .tag {{ background: #007bff; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 5px; }}
        .conversation-separator {{ border: none; height: 2px; background: linear-gradient(to right, #007bff, transparent); margin: 40px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Ghostman Conversation Export</h1>
        <div class="metadata">
            <table>
                <tr><td>Exported</td><td>{export_time}</td></tr>
                <tr><td>Conversations</td><td>{conversation_count}</td></tr>
                <tr><td>Format</td><td>HTML</td></tr>
            </table>
        </div>
""".format(
                    export_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    conversation_count=len(conversations)
                )
                f.write(html_template)
                
                for i, conversation in enumerate(conversations, 1):
                    # Conversation section
                    f.write(f'        <h2>{i}. {self._escape_html(conversation.title)}</h2>\n')
                    
                    # Metadata
                    f.write('        <div class="metadata">\n')
                    f.write('            <table>\n')
                    f.write(f'                <tr><td>Status</td><td>{conversation.status.value.title()}</td></tr>\n')
                    f.write(f'                <tr><td>Created</td><td>{conversation.created_at.strftime("%Y-%m-%d %H:%M:%S")}</td></tr>\n')
                    f.write(f'                <tr><td>Updated</td><td>{conversation.updated_at.strftime("%Y-%m-%d %H:%M:%S")}</td></tr>\n')
                    f.write(f'                <tr><td>Messages</td><td>{len(conversation.messages)}</td></tr>\n')
                    
                    if include_metadata and conversation.metadata:
                        if conversation.metadata.tags:
                            tags_html = ''.join(f'<span class="tag">{self._escape_html(tag)}</span>' for tag in conversation.metadata.tags)
                            f.write(f'                <tr><td>Tags</td><td>{tags_html}</td></tr>\n')
                        if conversation.metadata.category:
                            f.write(f'                <tr><td>Category</td><td>{self._escape_html(conversation.metadata.category)}</td></tr>\n')
                    
                    f.write('            </table>\n')
                    f.write('        </div>\n')
                    
                    # Summary
                    if conversation.summary:
                        f.write('        <div class="summary">\n')
                        f.write('            <h3>📝 Summary</h3>\n')
                        # Convert markdown in summary too
                        summary_html = self._markdown_to_html(conversation.summary.summary)
                        f.write(f'            <div>{summary_html}</div>\n')
                        if conversation.summary.key_topics:
                            topics_html = ''.join(f'<span class="tag">{self._escape_html(topic)}</span>' for topic in conversation.summary.key_topics)
                            f.write(f'            <p><strong>Key Topics:</strong> {topics_html}</p>\n')
                        f.write('        </div>\n')
                    
                    # Messages
                    for message in conversation.messages:
                        role_class = message.role.value.lower()
                        role_icon = {'system': '🔧', 'user': '👤', 'assistant': '🤖'}.get(role_class, '💬')
                        timestamp = message.timestamp.strftime('%H:%M:%S')
                        
                        f.write(f'        <div class="message {role_class}">\n')
                        f.write(f'            <div class="message-header">\n')
                        f.write(f'                <span>{role_icon} {message.role.value.upper()}</span>\n')
                        f.write(f'                <span class="timestamp">{timestamp}</span>\n')
                        f.write(f'            </div>\n')
                        # Convert markdown to HTML for better formatting
                        html_content = self._markdown_to_html(message.content)
                        f.write(f'            <div class="content">{html_content}</div>\n')
                        f.write(f'        </div>\n')
                    
                    if i < len(conversations):
                        f.write('        <hr class="conversation-separator">\n')
                
                # Write HTML footer
                f.write("""    </div>
</body>
</html>""")
            
            logger.info(f"✅ Exported {len(conversations)} conversations to HTML: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ HTML export failed: {e}")
            return False
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown text to HTML using markdown-it-py."""
        try:
            from markdown_it import MarkdownIt
            from markdown_it.plugins import plugin
            
            # Create markdown-it instance with plugins
            md = (
                MarkdownIt("commonmark")
                .enable(["table", "strikethrough"])  # Enable additional features
                .enable_many(["replacements", "smartquotes"])  # Typography improvements
            )
            
            # Configure for safety
            md.options.update({
                "html": False,  # Don't allow raw HTML for safety
                "linkify": True,  # Auto-linkify URLs
                "typographer": True,  # Smart quotes and dashes
                "breaks": True,  # Convert \n to <br>
            })
            
            # Convert markdown to HTML
            html = md.render(text)
            return html
            
        except ImportError:
            # If markdown-it-py not available, try the standard markdown library
            try:
                import markdown
                md = markdown.Markdown(extensions=[
                    'fenced_code',
                    'tables', 
                    'nl2br',
                    'sane_lists'
                ])
                return md.convert(text)
            except ImportError:
                # Fall back to basic conversion
                return self._basic_markdown_to_html(text)
    
    def _basic_markdown_to_html(self, text: str) -> str:
        """Basic markdown to HTML conversion without library."""
        import re
        
        # Escape HTML first
        html = self._escape_html(text)
        
        # Convert code blocks
        html = re.sub(r'```(\w+)?\n(.*?)\n```', r'<pre><code class="\1">\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Convert headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Convert bold and italic
        html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
        
        # Convert lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html, flags=re.DOTALL)
        
        # Convert blockquotes
        html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # Convert links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Convert line breaks
        html = html.replace('\n\n', '</p><p>').replace('\n', '<br>')
        html = f'<p>{html}</p>'
        
        return html
    
    async def get_export_formats(self) -> List[Dict[str, str]]:
        """Get available export formats."""
        return [
            {'format': 'json', 'name': 'JSON', 'extension': '.json', 'description': 'Machine-readable JSON format'},
            {'format': 'txt', 'name': 'Plain Text', 'extension': '.txt', 'description': 'Simple text format'},
            {'format': 'md', 'name': 'Markdown', 'extension': '.md', 'description': 'Markdown formatted text'},
            {'format': 'html', 'name': 'HTML', 'extension': '.html', 'description': 'Rich HTML format with styling'}
        ]