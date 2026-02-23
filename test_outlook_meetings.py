import pythoncom
import win32com.client
import traceback
from datetime import datetime

pythoncom.CoInitialize()

try:
    outlook = win32com.client.Dispatch('Outlook.Application')
    namespace = outlook.GetNamespace('MAPI')
    inbox = namespace.GetDefaultFolder(6)

    print('=' * 80)
    print('OUTLOOK COM MEETING EMAIL EXPLORATION')
    print('=' * 80)

    items = inbox.Items
    items.Sort('[ReceivedTime]', True)
    total = items.Count
    print(f'
Inbox total items: {total}')

