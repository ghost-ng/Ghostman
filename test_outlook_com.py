import pythoncom
import win32com.client
import traceback
from datetime import datetime, timedelta

Q = chr(39)

pythoncom.CoInitialize()

try:
    outlook = win32com.client.Dispatch('Outlook.Application')
    ns = outlook.GetNamespace('MAPI')
    sep = '=' * 70
    print(sep)
    print('OUTLOOK COM CAPABILITIES TEST')
    print(sep)
