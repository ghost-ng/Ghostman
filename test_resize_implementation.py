"""Test script for the frameless window resize implementation."""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QSize
from PyQt6.QtGui import QScreen

# Add the project to path
sys.path.insert(0, 'ghostman/src')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_resize_system():
    """Test the complete resize system."""
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("FRAMELESS WINDOW RESIZE SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Test imports
        print("\n1. Testing imports...")
        from presentation.ui.resize import ResizeManager
        from presentation.ui.resize.resize_mixin import AvatarResizableMixin, REPLResizableMixin
        from presentation.widgets.avatar_widget import AvatarWidget
        from presentation.widgets.floating_repl import FloatingREPLWindow
        print("✅ All imports successful")
        
        # Test avatar widget with resize
        print("\n2. Testing Avatar Widget resize...")
        avatar = AvatarWidget()
        if hasattr(avatar, 'resize_manager'):
            print("✅ Avatar has resize manager")
            if avatar.resize_manager:
                print(f"✅ Avatar resize active: min={avatar.resize_manager.constraints.min_size}, max={avatar.resize_manager.constraints.max_size}")
            else:
                print("⚠️ Avatar resize manager not initialized")
        else:
            print("❌ Avatar missing resize manager")
        
        # Test REPL window with resize
        print("\n3. Testing REPL Window resize...")
        repl = FloatingREPLWindow()
        if hasattr(repl, 'resize_manager'):
            print("✅ REPL has resize manager")
            if repl.resize_manager:
                print(f"✅ REPL resize active: min={repl.resize_manager.constraints.min_size}")
            else:
                print("⚠️ REPL resize manager not initialized")
        else:
            print("❌ REPL missing resize manager")
        
        # Test settings integration
        print("\n4. Testing settings integration...")
        try:
            from infrastructure.storage.settings_manager import settings
            resize_settings = settings.get('ui.resize', {})
            if resize_settings:
                print(f"✅ Resize settings found: {len(resize_settings)} options")
                print(f"   - Avatar enabled: {resize_settings.get('avatar_enabled', False)}")
                print(f"   - REPL enabled: {resize_settings.get('repl_enabled', False)}")
            else:
                print("⚠️ No resize settings found")
        except Exception as e:
            print(f"❌ Settings test failed: {e}")
        
        # Position windows for visual test
        screen = QScreen.availableGeometry(app.primaryScreen())
        
        # Show avatar
        avatar.move(100, 100)
        avatar.show()
        
        # Show REPL positioned relative to avatar
        repl.position_relative_to_avatar(
            QPoint(100, 100),  # Avatar position
            (120, 120),        # Avatar size
            screen
        )
        repl.show()
        
        print("\n" + "=" * 60)
        print("VISUAL TEST INSTRUCTIONS")
        print("=" * 60)
        print("\n🎯 Avatar Window Test (small square window):")
        print("   • Hover near edges/corners - cursor should change")
        print("   • Drag edges to resize (should maintain square aspect)")
        print("   • Size limits: 80x80 to 200x200 pixels")
        print("   • 6px resize border around window")
        
        print("\n🎯 REPL Window Test (large chat window):")
        print("   • Hover near edges/corners - cursor should change")
        print("   • Drag edges to resize freely")
        print("   • Minimum size: 360x320 pixels")
        print("   • 8px resize border around window")
        
        print("\n🎯 Integration Test:")
        print("   • Dragging window center should move (not resize)")
        print("   • Resize and drag should work together smoothly")
        print("   • Windows should stay always-on-top")
        
        print("\n💡 Tips:")
        print("   • Use precise mouse movements near window edges")
        print("   • Look for cursor changes indicating resize zones")
        print("   • Test all 8 resize zones (4 corners + 4 edges)")
        
        print("\nPress Ctrl+C to exit the test")
        print("=" * 60)
        
        app.exec()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all resize system files are in place")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_resize_system()