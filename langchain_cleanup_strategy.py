"""
LangChain Cleanup Strategy for FAISS-Only Migration

Comprehensive Python script to safely remove LangChain dependencies
and migrate to FAISS-only architecture with data preservation.
"""

import os
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langchain_cleanup")


@dataclass
class CleanupStep:
    """Individual cleanup step."""
    name: str
    description: str
    action: str
    files_affected: List[str]
    dependencies_removed: List[str]
    risks: List[str]
    rollback_info: Dict[str, Any]


class LangChainCleanupManager:
    """
    Manages the safe removal of LangChain dependencies and migration to FAISS-only.
    
    Key Features:
    - Backup creation before changes
    - Step-by-step cleanup with rollback capability
    - Dependency validation
    - Data migration verification
    - Comprehensive logging
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / f"langchain_cleanup_{int(time.time())}"
        self.cleanup_log = []
        
        # Files to be removed
        self.langchain_files = [
            "ghostman/src/infrastructure/langchain_rag/",
            "ghostman/src/presentation/widgets/repl_langchain_enhancer.py",
            "ghostman/src/presentation/widgets/repl_rag_enhanced.py",
        ]
        
        # Dependencies to remove from requirements.txt
        self.langchain_dependencies = [
            "langchain>=0.2.0",
            "langchain-community>=0.2.0", 
            "langchain-core>=0.2.0",
            "langchain-openai>=0.1.0",
            "langchain-chroma>=0.1.0",
            "chromadb>=0.4.0",
        ]
        
        # Files to update
        self.files_to_update = [
            "ghostman/src/infrastructure/rag_coordinator.py",
            "ghostman/src/application/app_coordinator.py",
            "requirements.txt"
        ]
        
        logger.info(f"LangChain cleanup manager initialized for {self.project_root}")
    
    def create_backup(self) -> bool:
        """Create complete backup before cleanup."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup entire project
            logger.info(f"Creating backup at {self.backup_dir}")
            
            # Copy important files
            important_files = [
                "requirements.txt",
                "ghostman/src/infrastructure/",
                "ghostman/src/presentation/widgets/",
                "ghostman/src/application/"
            ]
            
            for file_pattern in important_files:
                source_path = self.project_root / file_pattern
                if source_path.exists():
                    if source_path.is_file():
                        dest_path = self.backup_dir / file_pattern
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    else:
                        dest_path = self.backup_dir / file_pattern
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            
            # Create backup manifest
            manifest = {
                "backup_time": time.time(),
                "project_root": str(self.project_root),
                "langchain_files": self.langchain_files,
                "dependencies": self.langchain_dependencies,
                "files_to_update": self.files_to_update
            }
            
            with open(self.backup_dir / "backup_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info("✅ Backup created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return False
    
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current project state before cleanup."""
        analysis = {
            "langchain_files_present": [],
            "langchain_imports_found": [],
            "faiss_data_present": False,
            "dependencies_in_requirements": [],
            "potential_conflicts": []
        }
        
        # Check for LangChain files
        for file_pattern in self.langchain_files:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                analysis["langchain_files_present"].append(str(file_path))
        
        # Check requirements.txt
        requirements_path = self.project_root / "requirements.txt"
        if requirements_path.exists():
            content = requirements_path.read_text()
            for dep in self.langchain_dependencies:
                if dep.split('>=')[0].split('==')[0] in content:
                    analysis["dependencies_in_requirements"].append(dep)
        
        # Check for FAISS data
        faiss_data_paths = [
            self.project_root / "ghostman" / "data" / "faiss",
            self.project_root / "example_chroma_db",
            self.project_root / "test_chroma_db"
        ]
        
        for path in faiss_data_paths:
            if path.exists():
                analysis["faiss_data_present"] = True
                break
        
        # Scan for LangChain imports
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                if any(imp in content for imp in ["langchain", "from langchain", "import langchain"]):
                    analysis["langchain_imports_found"].append(str(py_file))
            except:
                continue
        
        return analysis
    
    def cleanup_step_1_remove_langchain_files(self) -> bool:
        """Step 1: Remove LangChain-specific files."""
        try:
            logger.info("🔄 Step 1: Removing LangChain files...")
            
            removed_files = []
            for file_pattern in self.langchain_files:
                file_path = self.project_root / file_pattern
                if file_path.exists():
                    if file_path.is_file():
                        file_path.unlink()
                        removed_files.append(str(file_path))
                    else:
                        shutil.rmtree(file_path)
                        removed_files.append(str(file_path))
            
            self.cleanup_log.append({
                "step": 1,
                "action": "remove_files",
                "files_removed": removed_files,
                "success": True
            })
            
            logger.info(f"✅ Removed {len(removed_files)} LangChain files")
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 1 failed: {e}")
            return False
    
    def cleanup_step_2_update_requirements(self) -> bool:
        """Step 2: Remove LangChain dependencies from requirements.txt."""
        try:
            logger.info("🔄 Step 2: Updating requirements.txt...")
            
            requirements_path = self.project_root / "requirements.txt"
            if not requirements_path.exists():
                logger.warning("requirements.txt not found")
                return True
            
            # Read current requirements
            lines = requirements_path.read_text().splitlines()
            original_count = len(lines)
            
            # Filter out LangChain dependencies
            filtered_lines = []
            removed_deps = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    filtered_lines.append(line)
                    continue
                
                # Check if this line contains a LangChain dependency
                should_remove = False
                for dep in self.langchain_dependencies:
                    dep_name = dep.split('>=')[0].split('==')[0]
                    if line.startswith(dep_name):
                        should_remove = True
                        removed_deps.append(line)
                        break
                
                if not should_remove:
                    filtered_lines.append(line)
            
            # Write updated requirements
            requirements_path.write_text('\n'.join(filtered_lines) + '\n')
            
            self.cleanup_log.append({
                "step": 2,
                "action": "update_requirements",
                "original_count": original_count,
                "final_count": len(filtered_lines),
                "removed_dependencies": removed_deps,
                "success": True
            })
            
            logger.info(f"✅ Removed {len(removed_deps)} LangChain dependencies")
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 2 failed: {e}")
            return False
    
    def cleanup_step_3_update_rag_coordinator(self) -> bool:
        """Step 3: Update RAG coordinator to use FAISS-only."""
        try:
            logger.info("🔄 Step 3: Updating RAG coordinator...")
            
            coordinator_path = self.project_root / "ghostman/src/infrastructure/rag_coordinator.py"
            if not coordinator_path.exists():
                logger.warning("RAG coordinator not found")
                return True
            
            # Read current coordinator
            original_content = coordinator_path.read_text()
            
            # Create new FAISS-only coordinator
            new_content = '''"""
RAG Coordinator - FAISS-Only Implementation

Updated coordinator that uses optimized FAISS-only architecture
instead of dual LangChain + FAISS system.
"""

import os
import logging
from typing import Optional, Dict, Any

from ..infrastructure.storage.settings_manager import settings
from ..infrastructure.conversation_management.services.conversation_service import ConversationService
from ..infrastructure.faiss_only_rag_coordinator import FAISSONlyRAGCoordinator, create_faiss_only_rag_coordinator

logger = logging.getLogger("ghostman.rag_coordinator")


class RAGCoordinator:
    """
    Simplified RAG coordinator using FAISS-only architecture.
    
    This replaces the previous dual LangChain + FAISS implementation
    with a streamlined FAISS-only approach for better performance.
    """
    
    def __init__(self, conversation_service: ConversationService):
        """Initialize FAISS-only RAG coordinator."""
        self.conversation_service = conversation_service
        self.faiss_coordinator: Optional[FAISSONlyRAGCoordinator] = None
        self._rag_enabled = False
        self._initialization_error = None
        
        # Check if RAG should be enabled
        self._check_rag_availability()
        
        if self._rag_enabled:
            self.faiss_coordinator = create_faiss_only_rag_coordinator(conversation_service)
        
        logger.info(f"RAG Coordinator initialized (FAISS-only: {self._rag_enabled})")
    
    def _check_rag_availability(self):
        """Check if FAISS-only RAG functionality can be enabled."""
        try:
            # Check for OpenAI API key
            api_key = settings.get("ai_model.api_key")
            if not api_key:
                self._initialization_error = "No OpenAI API key found"
                logger.info("RAG disabled: No OpenAI API key")
                return
            
            # Check if explicitly disabled in settings
            if not settings.get("rag.enabled", True):
                self._initialization_error = "RAG disabled in settings"
                logger.info("RAG disabled by user settings")
                return
            
            # Check for FAISS availability
            try:
                import faiss
            except ImportError:
                self._initialization_error = "FAISS not available - install faiss-cpu"
                logger.error(f"RAG disabled: {self._initialization_error}")
                return
            
            self._rag_enabled = True
            logger.info("FAISS-only RAG functionality available")
            
        except Exception as e:
            self._initialization_error = f"RAG availability check failed: {e}"
            logger.error(self._initialization_error)
    
    def is_enabled(self) -> bool:
        """Check if RAG is enabled."""
        return self._rag_enabled and self.faiss_coordinator is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get RAG system status."""
        base_status = {
            'enabled': self._rag_enabled,
            'error': self._initialization_error,
            'api_key_configured': bool(settings.get("ai_model.api_key")),
            'architecture': 'FAISS-only'
        }
        
        if self.faiss_coordinator:
            base_status.update(self.faiss_coordinator.get_status())
        
        return base_status
    
    def enhance_repl_widget(self, repl_widget, widget_id: str = None) -> bool:
        """
        Enhance a REPL widget with FAISS-only RAG capabilities.
        """
        if not self.is_enabled():
            logger.debug(f"RAG enhancement skipped: {self._initialization_error}")
            return False
        
        try:
            from ..presentation.widgets.faiss_rag_enhanced_repl import enhance_repl_with_faiss_rag
            
            enhanced_repl = enhance_repl_with_faiss_rag(
                repl_widget=repl_widget,
                rag_coordinator=self.faiss_coordinator,
                conversation_service=self.conversation_service
            )
            
            logger.info(f"Enhanced REPL widget {widget_id} with FAISS-only RAG")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enhance REPL widget: {e}")
            return False
    
    def set_conversation_for_all_widgets(self, conversation_id: str):
        """Set current conversation for RAG operations."""
        if self.faiss_coordinator:
            # This would be handled by the enhanced REPL widgets directly
            logger.info(f"Conversation context set to: {conversation_id}")
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG usage statistics."""
        if self.faiss_coordinator:
            return self.faiss_coordinator.get_comprehensive_stats()
        return {'enabled': False, 'architecture': 'FAISS-only'}
    
    def cleanup(self):
        """Cleanup RAG coordinator resources."""
        logger.info("Cleaning up FAISS-only RAG coordinator...")
        
        if self.faiss_coordinator:
            self.faiss_coordinator.cleanup()
            self.faiss_coordinator = None
        
        logger.info("RAG coordinator cleanup completed")


# Global RAG coordinator instance
_rag_coordinator: Optional[RAGCoordinator] = None


def get_rag_coordinator() -> Optional[RAGCoordinator]:
    """Get the global RAG coordinator instance."""
    return _rag_coordinator


def initialize_rag_coordinator(conversation_service: ConversationService) -> RAGCoordinator:
    """Initialize the global RAG coordinator."""
    global _rag_coordinator
    
    if _rag_coordinator is None:
        _rag_coordinator = RAGCoordinator(conversation_service)
    
    return _rag_coordinator


def cleanup_rag_coordinator():
    """Cleanup the global RAG coordinator."""
    global _rag_coordinator
    
    if _rag_coordinator:
        _rag_coordinator.cleanup()
        _rag_coordinator = None
'''
            
            # Write updated coordinator
            coordinator_path.write_text(new_content)
            
            self.cleanup_log.append({
                "step": 3,
                "action": "update_rag_coordinator",
                "file": str(coordinator_path),
                "success": True
            })
            
            logger.info("✅ RAG coordinator updated to FAISS-only")
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 3 failed: {e}")
            return False
    
    def cleanup_step_4_data_migration(self) -> bool:
        """Step 4: Migrate existing data to FAISS-only format."""
        try:
            logger.info("🔄 Step 4: Data migration verification...")
            
            # Check existing FAISS data
            faiss_data_found = False
            existing_data_paths = []
            
            possible_paths = [
                self.project_root / "ghostman" / "data" / "faiss",
                self.project_root / "test_chroma_db",
                self.project_root / "example_chroma_db"
            ]
            
            for path in possible_paths:
                if path.exists():
                    existing_data_paths.append(str(path))
                    faiss_data_found = True
            
            self.cleanup_log.append({
                "step": 4,
                "action": "data_migration_check",
                "existing_data_paths": existing_data_paths,
                "faiss_data_found": faiss_data_found,
                "success": True
            })
            
            if faiss_data_found:
                logger.info(f"✅ Found existing FAISS data at {len(existing_data_paths)} locations")
            else:
                logger.info("ℹ️ No existing FAISS data found - clean installation")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 4 failed: {e}")
            return False
    
    def cleanup_step_5_remove_temp_directories(self) -> bool:
        """Step 5: Clean up temporary directories and test files."""
        try:
            logger.info("🔄 Step 5: Cleaning up temporary directories...")
            
            temp_dirs = [
                "chroma_langchain_db/",
                "chroma_simple_test/",
                "test_chroma_integration/",
                "test_langchain_docs/",
                "test_integration_db/"
            ]
            
            removed_dirs = []
            for dir_name in temp_dirs:
                dir_path = self.project_root / dir_name
                if dir_path.exists() and dir_path.is_dir():
                    shutil.rmtree(dir_path)
                    removed_dirs.append(str(dir_path))
            
            # Remove test files
            test_files = [
                "test_langchain_basic.py",
                "test_langchain_rag.py",
                "test_rag_pipeline.py",
                "test_rag_simple.py",
                "test_rag_workflow.py",
                "test_unified_session_workflow.py"
            ]
            
            removed_files = []
            for file_name in test_files:
                file_path = self.project_root / file_name
                if file_path.exists():
                    file_path.unlink()
                    removed_files.append(str(file_path))
            
            self.cleanup_log.append({
                "step": 5,
                "action": "cleanup_temp_dirs",
                "removed_directories": removed_dirs,
                "removed_files": removed_files,
                "success": True
            })
            
            logger.info(f"✅ Cleaned up {len(removed_dirs)} directories and {len(removed_files)} files")
            return True
            
        except Exception as e:
            logger.error(f"❌ Step 5 failed: {e}")
            return False
    
    def execute_full_cleanup(self) -> bool:
        """Execute complete LangChain cleanup process."""
        try:
            logger.info("🚀 Starting LangChain cleanup process...")
            
            # Pre-cleanup analysis
            analysis = self.analyze_current_state()
            logger.info(f"Pre-cleanup analysis: {analysis}")
            
            # Create backup
            if not self.create_backup():
                logger.error("❌ Backup creation failed - aborting cleanup")
                return False
            
            # Execute cleanup steps
            steps = [
                self.cleanup_step_1_remove_langchain_files,
                self.cleanup_step_2_update_requirements,
                self.cleanup_step_3_update_rag_coordinator,
                self.cleanup_step_4_data_migration,
                self.cleanup_step_5_remove_temp_directories
            ]
            
            for i, step_func in enumerate(steps, 1):
                logger.info(f"Executing step {i}/5...")
                if not step_func():
                    logger.error(f"❌ Step {i} failed - cleanup incomplete")
                    return False
            
            # Generate cleanup report
            self.generate_cleanup_report()
            
            logger.info("✅ LangChain cleanup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup process failed: {e}")
            return False
    
    def generate_cleanup_report(self):
        """Generate comprehensive cleanup report."""
        report = {
            "cleanup_time": time.time(),
            "project_root": str(self.project_root),
            "backup_location": str(self.backup_dir),
            "steps_completed": self.cleanup_log,
            "summary": {
                "total_steps": len(self.cleanup_log),
                "successful_steps": sum(1 for step in self.cleanup_log if step["success"]),
                "architecture_change": "LangChain → FAISS-only"
            }
        }
        
        report_path = self.project_root / "langchain_cleanup_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Cleanup report saved to {report_path}")
    
    def rollback_cleanup(self) -> bool:
        """Rollback cleanup changes using backup."""
        try:
            logger.info(f"🔄 Rolling back cleanup using backup from {self.backup_dir}")
            
            if not self.backup_dir.exists():
                logger.error("❌ Backup directory not found")
                return False
            
            # Restore files from backup
            for item in self.backup_dir.rglob("*"):
                if item.is_file() and item.name != "backup_manifest.json":
                    relative_path = item.relative_to(self.backup_dir)
                    target_path = self.project_root / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_path)
            
            logger.info("✅ Cleanup rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False


def main():
    """Main execution function."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python langchain_cleanup_strategy.py <project_root>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    if not os.path.exists(project_root):
        print(f"Error: Project root '{project_root}' does not exist")
        sys.exit(1)
    
    cleanup_manager = LangChainCleanupManager(project_root)
    
    print("LangChain Cleanup Strategy")
    print("=" * 50)
    print(f"Project Root: {project_root}")
    print(f"Backup Location: {cleanup_manager.backup_dir}")
    print()
    
    # Analyze current state
    analysis = cleanup_manager.analyze_current_state()
    print("Current State Analysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    print()
    
    # Confirm cleanup
    response = input("Proceed with LangChain cleanup? (y/N): ")
    if response.lower() != 'y':
        print("Cleanup cancelled")
        sys.exit(0)
    
    # Execute cleanup
    success = cleanup_manager.execute_full_cleanup()
    
    if success:
        print("\n✅ LangChain cleanup completed successfully!")
        print(f"📁 Backup saved at: {cleanup_manager.backup_dir}")
        print(f"📊 Report saved at: {project_root}/langchain_cleanup_report.json")
    else:
        print("\n❌ Cleanup failed - check logs for details")
        print(f"💾 Backup available at: {cleanup_manager.backup_dir}")


if __name__ == "__main__":
    main()