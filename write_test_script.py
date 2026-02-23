import os, textwrap

path = os.path.join(os.getcwd(), "test_outlook_com.py")

script = textwrap.dedent("""
import pythoncom
import win32com.client
import traceback
from datetime import datetime, timedelta

Q = chr(39)

pythoncom.CoInitialize()

try:
    outlook = win32com.client.Dispatch("Outlook.Application")
    ns = outlook.GetNamespace("MAPI")
    sep = "=" * 70
    print(sep)
    print("OUTLOOK COM CAPABILITIES TEST")
    print(sep)
    print()

    print("TEST 1: CURRENT USER and ACCOUNT INFO")
    print(sep)
    try:
        cu = ns.CurrentUser
        print(f"  ns.CurrentUser: {cu}")
        for p in ["Name", "Address", "Type"]:
            try: print(f"    .{p}: {getattr(cu, p)}")
            except Exception as e: print(f"    .{p} FAILED: {e}")
    except Exception as e: print(f"  ns.CurrentUser FAILED: {e}")

except Exception as e:
    print(f"FATAL: {e}")
finally:
    pythoncom.CoUninitialize()
""")

with open(path, "w") as f:
    f.write(script)
print(f"Written to {path}")
