"""
File Search Skill - Search local files using Windows Search API.

This skill searches for files on the local system using Windows Search indexer.
Respects user-level permissions and never accesses system files.
"""

import logging
from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..interfaces.base_skill import (
    BaseSkill,
    SkillMetadata,
    SkillParameter,
    SkillResult,
    PermissionType,
    SkillCategory,
)

logger = logging.getLogger("ghostman.skills.file_search")


class FileSearchSkill(BaseSkill):
    """
    Skill for searching files using Windows Search API.

    Searches the Windows Search index for files matching criteria like
    filename, content, file type, and date modified. Returns results
    with full file paths and metadata.

    Requirements:
        - Windows Search service running
        - pywin32 package for COM automation

    Example:
        >>> skill = FileSearchSkill()
        >>> result = await skill.execute(
        ...     filename="report",
        ...     file_type="pdf",
        ...     modified_days=7
        ... )
        >>> print(result.data["results"])
        [{"path": "C:\\Users\\...\\report.pdf", "size": 1024, ...}]
    """

    @property
    def metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        return SkillMetadata(
            skill_id="file_search",
            name="File Search",
            description="Search for files on your computer using Windows Search",
            category=SkillCategory.FILE_MANAGEMENT,
            icon="🔍",
            enabled_by_default=True,
            requires_confirmation=False,  # Safe read-only operation
            permissions_required=[PermissionType.FILE_SYSTEM_READ],
            version="1.0.0",
            author="Ghostman"
        )

    @property
    def parameters(self) -> List[SkillParameter]:
        """Return list of parameters this skill accepts."""
        return [
            SkillParameter(
                name="filename",
                type=str,
                required=False,
                description="Filename to search for (partial match)",
                default="",
                constraints={"max_length": 255}
            ),
            SkillParameter(
                name="content",
                type=str,
                required=False,
                description="Search within file contents",
                default="",
                constraints={"max_length": 255}
            ),
            SkillParameter(
                name="file_type",
                type=str,
                required=False,
                description="File extension (e.g., 'pdf', 'docx', 'txt')",
                default="",
                constraints={"max_length": 10}
            ),
            SkillParameter(
                name="modified_days",
                type=int,
                required=False,
                description="Modified within last N days (0 = any time)",
                default=0,
                constraints={"min": 0, "max": 3650}  # 0 to 10 years
            ),
            SkillParameter(
                name="max_results",
                type=int,
                required=False,
                description="Maximum number of results to return",
                default=50,
                constraints={"min": 1, "max": 500}
            ),
            SkillParameter(
                name="search_path",
                type=str,
                required=False,
                description="Limit search to specific folder path",
                default="",
                constraints={"max_length": 500}
            ),
        ]

    def _build_aqs_query(self, params: Dict[str, Any]) -> str:
        """
        Build Advanced Query Syntax (AQS) query for Windows Search.

        AQS is the query language used by Windows Search indexer.

        Args:
            params: Validated search parameters

        Returns:
            AQS query string
        """
        conditions = []

        # Filename filter
        if params.get("filename"):
            # Use System.FileName for partial matches
            filename = params["filename"].replace("'", "''")  # Escape quotes
            conditions.append(f"System.FileName:~\"{filename}\"")

        # Content filter (full-text search)
        if params.get("content"):
            content = params["content"].replace("'", "''")
            conditions.append(f"System.Search.Contents:\"{content}\"")

        # File type filter
        if params.get("file_type"):
            ext = params["file_type"].strip().lower().lstrip(".")
            conditions.append(f"System.FileExtension:=\".{ext}\"")

        # Modified date filter
        if params.get("modified_days", 0) > 0:
            days = params["modified_days"]
            cutoff_date = datetime.now() - timedelta(days=days)
            # Format: YYYY-MM-DD
            date_str = cutoff_date.strftime("%Y-%m-%d")
            conditions.append(f"System.DateModified:>={date_str}")

        # Search path filter
        if params.get("search_path"):
            search_path = params["search_path"].replace("\\", "\\\\")
            conditions.append(f"System.ItemPathDisplay:~\"{search_path}\"")

        # Combine conditions with AND
        if conditions:
            return " AND ".join(conditions)
        else:
            # No filters - match all files
            return "System.Kind:=System.Kind.Document OR System.Kind:=System.Kind.Picture OR System.Kind:=System.Kind.Video"

    async def execute(self, **params: Any) -> SkillResult:
        """
        Execute the file search skill.

        Searches Windows Search index for files matching the given criteria.

        Args:
            **params: Validated parameters (filename, content, file_type, etc.)

        Returns:
            SkillResult with list of matching files
        """
        try:
            # Import win32com (only when needed)
            try:
                import win32com.client
                import pythoncom
            except ImportError:
                return SkillResult(
                    success=False,
                    message="Windows Search integration not available",
                    error="pywin32 package not installed. Run: pip install pywin32"
                )

            # Check if at least one search criterion is provided
            has_criteria = any([
                params.get("filename"),
                params.get("content"),
                params.get("file_type"),
                params.get("modified_days", 0) > 0,
                params.get("search_path"),
            ])

            if not has_criteria:
                return SkillResult(
                    success=False,
                    message="No search criteria provided",
                    error="Please provide at least one search parameter (filename, content, file_type, etc.)"
                )

            # Initialize COM for this thread
            pythoncom.CoInitialize()

            try:
                # Connect to Windows Search
                try:
                    connection = win32com.client.Dispatch("ADODB.Connection")
                    recordset = win32com.client.Dispatch("ADODB.Recordset")
                except Exception as e:
                    logger.error(f"Failed to connect to Windows Search: {e}")
                    return SkillResult(
                        success=False,
                        message="Could not connect to Windows Search",
                        error=f"Windows Search service may not be running: {str(e)}"
                    )

                # Build AQS query
                aqs_query = self._build_aqs_query(params)
                logger.debug(f"AQS Query: {aqs_query}")

                # Build SQL query for Windows Search
                # Select common file properties
                sql_query = f"""
                SELECT TOP {params.get('max_results', 50)}
                    System.ItemPathDisplay,
                    System.FileName,
                    System.Size,
                    System.DateModified,
                    System.FileExtension,
                    System.Kind
                FROM SystemIndex
                WHERE {aqs_query}
                ORDER BY System.DateModified DESC
                """

                # Connect and execute query
                connection.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
                recordset.Open(sql_query, connection)

                # Collect results
                results = []
                while not recordset.EOF:
                    try:
                        file_path = recordset.Fields("System.ItemPathDisplay").Value
                        file_name = recordset.Fields("System.FileName").Value
                        file_size = recordset.Fields("System.Size").Value or 0
                        date_modified = recordset.Fields("System.DateModified").Value
                        file_ext = recordset.Fields("System.FileExtension").Value or ""
                        file_kind = recordset.Fields("System.Kind").Value or ""

                        # Convert date to ISO format
                        if date_modified:
                            try:
                                date_str = date_modified.isoformat() if hasattr(date_modified, 'isoformat') else str(date_modified)
                            except:
                                date_str = ""
                        else:
                            date_str = ""

                        results.append({
                            "path": str(file_path) if file_path else "",
                            "name": str(file_name) if file_name else "",
                            "size_bytes": int(file_size),
                            "size_readable": self._format_file_size(file_size),
                            "modified": date_str,
                            "extension": str(file_ext),
                            "type": str(file_kind),
                        })

                        recordset.MoveNext()
                    except Exception as e:
                        logger.warning(f"Error reading record: {e}")
                        recordset.MoveNext()
                        continue

                # Close connections
                recordset.Close()
                connection.Close()

                logger.info(f"✓ File search found {len(results)} results")

                return SkillResult(
                    success=True,
                    message=f"Found {len(results)} file(s) matching your search",
                    data={
                        "results": results,
                        "count": len(results),
                        "query": aqs_query,
                        "max_results": params.get("max_results", 50),
                    },
                    action_taken=f"Searched for files: {aqs_query}",
                )

            finally:
                pythoncom.CoUninitialize()

        except Exception as e:
            logger.error(f"File search skill failed: {e}", exc_info=True)
            return SkillResult(
                success=False,
                message="File search failed",
                error=str(e)
            )

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    async def on_success(self, result: SkillResult) -> None:
        """Log successful file search."""
        count = result.data.get("count", 0)
        logger.info(f"File search skill succeeded: {count} results")

    async def on_error(self, result: SkillResult) -> None:
        """Log file search failure."""
        logger.warning(f"File search skill failed: {result.error}")
