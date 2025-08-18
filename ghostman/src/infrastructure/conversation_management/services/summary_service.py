"""
AI-powered conversation summary service.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.conversation import ConversationSummary
from ..repositories.conversation_repository import ConversationRepository

logger = logging.getLogger("ghostman.summary_service")


class SummaryService:
    """Service for generating AI-powered conversation summaries."""
    
    SUMMARY_PROMPT_TEMPLATE = """
Please analyze the following conversation and provide a comprehensive summary.

Conversation Title: {title}
Message Count: {message_count}
Date Range: {date_range}

Conversation Content:
{content}

Please provide your response in the following JSON format:
{{
    "summary": "A concise 2-3 sentence summary of the conversation",
    "key_topics": ["topic1", "topic2", "topic3"],
    "main_themes": "Brief description of the main themes discussed",
    "outcome": "What was accomplished or concluded, if any",
    "confidence": 0.85
}}

Focus on:
1. The main purpose and outcome of the conversation
2. Key technical concepts or decisions discussed
3. Important information or insights gained
4. Any action items or next steps mentioned

Keep the summary concise but comprehensive enough to understand the conversation's value without reading the full content.
"""

    TITLE_PROMPT_TEMPLATE = """
Please generate a concise, descriptive title for this conversation based on its content.

Conversation Content:
{content}

Requirements:
- Maximum 6 words
- Capture the main topic or purpose
- Use active, descriptive language
- No generic words like "conversation", "chat", "discussion"
- Focus on what was accomplished or discussed

Examples:
- "Implement SQLAlchemy Migration System"
- "Fix PyQt Avatar Jumping"
- "Debug API Integration Issues"
- "Create User Authentication Flow"

Respond with ONLY the title, no other text.
"""
    
    def __init__(self, repository: ConversationRepository):
        """Initialize summary service."""
        self.repository = repository
        self._ai_service = None
    
    async def generate_summary(self, conversation_id: str) -> bool:
        """Generate AI summary for a conversation."""
        try:
            # Load conversation
            conversation = await self.repository.get_conversation(conversation_id, include_messages=True)
            if not conversation or not conversation.messages:
                logger.warning(f"No conversation found or no messages: {conversation_id}")
                return False
            
            # Skip if conversation is too short
            user_messages = [msg for msg in conversation.messages if msg.role.value == "user"]
            assistant_messages = [msg for msg in conversation.messages if msg.role.value == "assistant"]
            
            if len(user_messages) < 2 or len(assistant_messages) < 1:
                logger.info(f"Conversation too short for summary: {conversation_id}")
                return False
            
            # Get AI service
            ai_service = await self._get_ai_service()
            if not ai_service:
                logger.error("AI service not available for summary generation")
                return False
            
            # Prepare content for summarization
            summary_content = self._prepare_content_for_summary(conversation)
            
            # Generate summary prompt
            prompt = self._build_summary_prompt(conversation, summary_content)
            
            # Call AI service asynchronously
            logger.info(f"Generating summary for conversation: {conversation_id}")
            result = await ai_service.send_message_async(prompt)
            
            if not result.get('success', False):
                logger.error(f"AI summary generation failed: {result.get('error', 'Unknown error')}")
                return False
            
            # Parse AI response
            summary_data = self._parse_summary_response(result['response'])
            if not summary_data:
                logger.error("Failed to parse AI summary response")
                return False
            
            # Create summary object
            summary = ConversationSummary.create(
                conversation_id=conversation_id,
                summary=summary_data['summary'],
                key_topics=summary_data['key_topics'],
                model_used=ai_service.current_config.get('model_name'),
                confidence_score=summary_data.get('confidence')
            )
            
            # Save summary
            success = await self.repository.save_conversation_summary(summary)
            
            if success:
                logger.info(f"✅ Generated summary for conversation: {conversation_id}")
            else:
                logger.error(f"❌ Failed to save summary for conversation: {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed for {conversation_id}: {e}")
            return False
    
    async def generate_title(self, conversation_id: str) -> Optional[str]:
        """Generate an AI-powered title for a conversation."""
        try:
            # Load conversation
            conversation = await self.repository.get_conversation(conversation_id, include_messages=True)
            if not conversation or not conversation.messages:
                logger.warning(f"No conversation found or no messages: {conversation_id}")
                return None
            
            # Skip if conversation is too short
            user_messages = [msg for msg in conversation.messages if msg.role.value == "user"]
            if len(user_messages) < 1:
                logger.info(f"Conversation too short for title generation: {conversation_id}")
                return None
            
            # Get AI service
            ai_service = await self._get_ai_service()
            if not ai_service:
                logger.error("AI service not available for title generation")
                return None
            
            # Prepare content for title generation (first few messages)
            title_content = self._prepare_content_for_title(conversation)
            
            # Generate title prompt
            prompt = self.TITLE_PROMPT_TEMPLATE.format(content=title_content)
            
            # Call AI service asynchronously
            logger.info(f"Generating title for conversation: {conversation_id}")
            result = await ai_service.send_message_async(prompt)
            
            if not result.get('success', False):
                logger.error(f"AI title generation failed: {result.get('error', 'Unknown error')}")
                return None
            
            # Parse response and clean title
            title = result['response'].strip()
            title = title.replace('"', '').replace("'", '').strip()
            
            # Limit title length
            if len(title) > 100:
                title = title[:97] + "..."
            
            if title:
                logger.info(f"✅ Generated title for conversation {conversation_id}: {title}")
                return title
            else:
                logger.warning(f"Empty title generated for conversation: {conversation_id}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Title generation failed for {conversation_id}: {e}")
            return None
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        """Get existing conversation summary."""
        try:
            conversation = await self.repository.get_conversation(conversation_id, include_messages=False)
            return conversation.summary if conversation else None
        except Exception as e:
            logger.error(f"❌ Failed to get summary for {conversation_id}: {e}")
            return None
    
    async def regenerate_summary(self, conversation_id: str) -> bool:
        """Regenerate summary for a conversation (overwrites existing)."""
        # Same as generate_summary - it will overwrite existing summary
        return await self.generate_summary(conversation_id)
    
    async def batch_generate_summaries(
        self,
        conversation_ids: List[str],
        skip_existing: bool = True
    ) -> Dict[str, bool]:
        """Generate summaries for multiple conversations."""
        results = {}
        
        for conv_id in conversation_ids:
            try:
                # Skip if summary already exists and skip_existing is True
                if skip_existing:
                    existing = await self.get_conversation_summary(conv_id)
                    if existing:
                        results[conv_id] = True
                        continue
                
                # Generate summary
                success = await self.generate_summary(conv_id)
                results[conv_id] = success
                
                # Add small delay to avoid overwhelming AI service
                import asyncio
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Batch summary failed for {conv_id}: {e}")
                results[conv_id] = False
        
        return results
    
    def _prepare_content_for_summary(self, conversation) -> str:
        """Prepare conversation content for summarization."""
        content_parts = []
        
        for message in conversation.messages:
            # Skip system messages for summary
            if message.role.value == "system":
                continue
            
            role_label = "User" if message.role.value == "user" else "Assistant"
            content_parts.append(f"{role_label}: {message.content}")
        
        return "\n\n".join(content_parts)
    
    def _prepare_content_for_title(self, conversation) -> str:
        """Prepare conversation content for title generation (first few messages only)."""
        content_parts = []
        message_count = 0
        
        for message in conversation.messages:
            # Skip system messages for title
            if message.role.value == "system":
                continue
            
            # Only use first few messages for title generation
            if message_count >= 4:
                break
            
            role_label = "User" if message.role.value == "user" else "Assistant"
            content_parts.append(f"{role_label}: {message.content}")
            message_count += 1
        
        content = "\n\n".join(content_parts)
        # Limit content length for title generation
        return content[:1000] + "..." if len(content) > 1000 else content
    
    def _build_summary_prompt(self, conversation, content: str) -> str:
        """Build the AI prompt for summary generation."""
        # Calculate date range
        if conversation.messages:
            first_msg = conversation.messages[0]
            last_msg = conversation.messages[-1]
            date_range = f"{first_msg.timestamp.strftime('%Y-%m-%d %H:%M')} to {last_msg.timestamp.strftime('%Y-%m-%d %H:%M')}"
        else:
            date_range = "Unknown"
        
        return self.SUMMARY_PROMPT_TEMPLATE.format(
            title=conversation.title,
            message_count=len(conversation.messages),
            date_range=date_range,
            content=content[:4000]  # Limit content length to avoid token limits
        )
    
    def _parse_summary_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI summary response."""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            
            # Look for JSON block
            json_start = response.find('{')
            json_end = response.rfind('}')
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end+1]
                summary_data = json.loads(json_str)
                
                # Validate required fields
                if 'summary' in summary_data and 'key_topics' in summary_data:
                    # Ensure key_topics is a list
                    if isinstance(summary_data['key_topics'], str):
                        summary_data['key_topics'] = [summary_data['key_topics']]
                    elif not isinstance(summary_data['key_topics'], list):
                        summary_data['key_topics'] = []
                    
                    return summary_data
            
            # Fallback: treat entire response as summary
            logger.warning("Could not parse JSON from summary response, using fallback")
            return {
                'summary': response[:500],  # Limit length
                'key_topics': [],
                'confidence': 0.5
            }
            
        except Exception as e:
            logger.error(f"Failed to parse summary response: {e}")
            return None
    
    async def _get_ai_service(self):
        """Get AI service instance."""
        if self._ai_service:
            return self._ai_service
        
        try:
            # Import AI service
            from ...ai.ai_service import AIService
            
            # Create new AI service instance
            ai_service = AIService()
            
            # Initialize with current settings
            if ai_service.initialize():
                self._ai_service = ai_service
                return ai_service
            else:
                logger.error("Failed to initialize AI service for summaries")
                return None
                
        except ImportError as e:
            logger.error(f"AI service not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get AI service: {e}")
            return None
    
    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get statistics about conversation summaries."""
        try:
            stats = await self.repository.get_conversation_stats()
            
            # Add summary-specific stats
            summary_stats = {
                'total_summaries': stats.get('summaries', 0),
                'total_conversations': stats.get('conversations', 0),
                'summary_coverage': 0.0
            }
            
            if summary_stats['total_conversations'] > 0:
                summary_stats['summary_coverage'] = (
                    summary_stats['total_summaries'] / summary_stats['total_conversations']
                )
            
            return summary_stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get summary statistics: {e}")
            return {}
    
    def shutdown(self):
        """Shutdown the summary service."""
        if self._ai_service:
            try:
                self._ai_service.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down AI service: {e}")
            finally:
                self._ai_service = None
        
        logger.info("Summary service shut down")