"""Quick diagnostic script to test Outlook COM filter syntax."""
import pythoncom
import win32com.client
from datetime import datetime, timedelta

pythoncom.CoInitialize()
try:
    outlook = win32com.client.Dispatch("Outlook.Application")
    ns = outlook.GetNamespace("MAPI")

    # Test Inbox
    inbox = ns.GetDefaultFolder(6)
    print(f"Inbox folder: {inbox.Name}")
    print(f"Inbox total items: {inbox.Items.Count}")

    # Test Sent
    sent = ns.GetDefaultFolder(5)
    print(f"Sent folder: {sent.Name}")
    print(f"Sent total items: {sent.Items.Count}")

    # Get first item to see what ReceivedTime looks like
    items = inbox.Items
    items.Sort("[ReceivedTime]", True)
    first = items.GetFirst()
    if first:
        print(f"\nFirst inbox item:")
        print(f"  Subject: {first.Subject}")
        print(f"  ReceivedTime: {first.ReceivedTime}")
        print(f"  ReceivedTime type: {type(first.ReceivedTime)}")
        print(f"  SenderName: {first.SenderName}")

    # Test date filter formats
    cutoff = datetime.now() - timedelta(days=30)

    # Format 1: M/d/yyyy h:mm AM/PM (current approach)
    h12 = cutoff.hour % 12 or 12
    ap = "AM" if cutoff.hour < 12 else "PM"
    fmt1 = f"{cutoff.month}/{cutoff.day}/{cutoff.year} {h12}:{cutoff.minute:02d} {ap}"

    # Format 2: strftime with leading zeros
    fmt2 = cutoff.strftime("%m/%d/%Y %I:%M %p")

    # Format 3: Short format M/d/yyyy only
    fmt3 = f"{cutoff.month}/{cutoff.day}/{cutoff.year}"

    for label, date_str in [("No-leading-zeros AM/PM", fmt1), ("strftime", fmt2), ("Date only", fmt3)]:
        filt = f"[ReceivedTime] >= '{date_str}'"
        print(f"\nTesting Jet filter: {filt}")
        try:
            items2 = inbox.Items
            items2.Sort("[ReceivedTime]", True)
            restricted = items2.Restrict(filt)
            # Try GetFirst to see if there are results
            first_r = restricted.GetFirst()
            count = 0
            while first_r is not None and count < 5:
                count += 1
                first_r = restricted.GetNext()
            print(f"  Result: at least {count} items (checked up to 5)")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Test with no filter at all - just iterate first 3
    print(f"\nNo filter, just iterating first 3 inbox items:")
    items3 = inbox.Items
    items3.Sort("[ReceivedTime]", True)
    item = items3.GetFirst()
    i = 0
    while item is not None and i < 3:
        try:
            print(f"  [{i}] {item.SenderName}: {item.Subject} ({item.ReceivedTime})")
        except:
            print(f"  [{i}] (error reading item)")
        item = items3.GetNext()
        i += 1

    # Test DASL sender filter
    print(f"\nTesting DASL sender filter on inbox (no date restriction):")
    try:
        items4 = inbox.Items
        dasl = '@SQL="urn:schemas:httpmail:sendername" like \'%lydia%\''
        print(f"  Filter: {dasl}")
        restricted2 = items4.Restrict(dasl)
        first_d = restricted2.GetFirst()
        count2 = 0
        while first_d is not None and count2 < 5:
            try:
                print(f"  [{count2}] {first_d.SenderName}: {first_d.Subject}")
            except:
                pass
            count2 += 1
            first_d = restricted2.GetNext()
        print(f"  Found: {count2} items (checked up to 5)")
    except Exception as e:
        print(f"  DASL ERROR: {e}")

    # Test Windows locale
    import locale
    print(f"\nSystem locale: {locale.getdefaultlocale()}")
    print(f"Date format test: {datetime.now().strftime('%x %X')}")

finally:
    pythoncom.CoUninitialize()
    print("\nDone.")
