#!/usr/bin/env python
"""Quick import test to catch any issues before running the system."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")
    
    try:
        print("  Importing config...", end=" ")
        from backend.ai_tagging import config
        print("✓")
        
        print("  Importing schemas...", end=" ")
        from backend.ai_tagging import schemas
        print("✓")
        
        print("  Importing rate_limiter...", end=" ")
        from backend.ai_tagging import rate_limiter
        print("✓")
        
        print("  Importing gemini_client...", end=" ")
        from backend.ai_tagging import gemini_client
        print("✓")
        
        print("  Importing db_integration...", end=" ")
        from backend.ai_tagging import db_integration
        print("✓")
        
        print("  Importing tagging_service...", end=" ")
        from backend.ai_tagging import tagging_service
        print("✓")
        
        print("  Importing main package...", end=" ")
        from backend import ai_tagging
        print("✓")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
