import datetime
import glob
import re

# Compute build date + 365 days
target_date = datetime.date.today() + datetime.timedelta(days=365)
valid_until = target_date.isoformat()

count = 0
for f in sorted(glob.glob("products/*.html")):
    with open(f, "r", encoding="utf-8") as fp:
        c = fp.read()
    if '"priceValidUntil":' in c:
        c_new = re.sub(r'"priceValidUntil":\s*"[^"]+"', f'"priceValidUntil": "{valid_until}"', c)
        if c_new != c:
            with open(f, "w", encoding="utf-8") as fp:
                fp.write(c_new)
            count += 1
print(f"Updated priceValidUntil to {valid_until} in {count} product files")
