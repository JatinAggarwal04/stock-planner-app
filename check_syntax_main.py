import sys
import py_compile

try:
    py_compile.compile('backend/main.py', doraise=True)
    print("Syntax check passed for backend/main.py")
except py_compile.PyCompileError as e:
    print(f"Syntax check failed: {e}")
    sys.exit(1)
