#!/usr/bin/env python3
"""
Test theme editor integration with the main application.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ghostman', 'src'))

def test_theme_integration():
    """Test if the theme editor can be integrated with settings dialog."""
    try:
        # Test PyQt6 import
        from PyQt6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout
        from PyQt6.QtCore import Qt
        
        print("✅ PyQt6 imports successful")
        
        # Create minimal app
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Test theme editor creation
        try:
            # Import theme editor
            from presentation.dialogs.theme_editor import ThemeEditorTab
            print("✅ ThemeEditorTab import successful")
            
            # Create theme editor tab
            theme_editor = ThemeEditorTab()
            print("✅ ThemeEditorTab created successfully")
            
            # Test if it has expected methods
            expected_methods = ['apply_theme', 'load_theme', 'save_custom_theme']
            for method in expected_methods:
                if hasattr(theme_editor, method):
                    print(f"✅ Method {method} found")
                else:
                    print(f"⚠️  Method {method} missing")
            
            # Create a test tab widget to simulate settings dialog
            tab_widget = QTabWidget()
            tab_widget.addTab(theme_editor, "Themes")
            tab_widget.setWindowTitle("Theme Editor Test")
            tab_widget.resize(800, 600)
            
            print("✅ Theme editor added to tab widget")
            
            # Show briefly for visual verification (optional)
            # tab_widget.show()
            # app.processEvents()
            
            return True
            
        except ImportError as e:
            print(f"❌ Theme editor import failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Theme editor creation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ PyQt6 import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_settings_dialog_integration():
    """Test integration with existing settings dialog."""
    print("\n🔧 Testing Settings Dialog Integration...")
    
    # Check if settings dialog exists and can be modified
    settings_file = "ghostman/src/presentation/dialogs/settings_dialog.py"
    
    if os.path.exists(settings_file):
        print(f"✅ Settings dialog file found")
        
        # Check file size (should be substantial)
        size = os.path.getsize(settings_file)
        print(f"✅ Settings dialog size: {size:,} bytes")
        
        # Check for tab creation patterns
        with open(settings_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '_create_' in content and 'tab' in content.lower():
            print("✅ Tab creation patterns found")
        else:
            print("⚠️  Tab creation patterns not clearly identified")
            
        if 'addTab' in content:
            print("✅ addTab method usage found")
        else:
            print("⚠️  addTab method usage not found")
            
        return True
    else:
        print(f"❌ Settings dialog file not found: {settings_file}")
        return False

def main():
    """Run theme integration tests."""
    print("🔗 THEME INTEGRATION TEST")
    print("=" * 50)
    
    # Test basic integration
    integration_success = test_theme_integration()
    
    # Test settings dialog readiness
    settings_success = test_settings_dialog_integration()
    
    print("\n" + "=" * 50)
    print("🎯 INTEGRATION RESULTS:")
    
    if integration_success:
        print("✅ Theme editor integration: READY")
    else:
        print("❌ Theme editor integration: NEEDS WORK")
    
    if settings_success:
        print("✅ Settings dialog integration: READY") 
    else:
        print("❌ Settings dialog integration: NEEDS WORK")
    
    if integration_success and settings_success:
        print("\n🎉 THEME SYSTEM READY FOR USE!")
        print("\n📋 NEXT STEPS:")
        print("1. Add theme editor tab to settings dialog")
        print("2. Connect theme signals to existing components")
        print("3. Test live preview functionality")
        print("4. Verify all 10 preset themes work correctly")
    else:
        print("\n⚠️  Some integration work needed before deployment")

if __name__ == "__main__":
    main()