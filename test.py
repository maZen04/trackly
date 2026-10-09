import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from trackly.models import Snapshot
from difflib import unified_diff

old = Snapshot.objects.get(id=19).content.splitlines()
new = Snapshot.objects.get(id=23).content.splitlines()

diff = list(unified_diff(
    old,
    new,
    fromfile="old",
    tofile="new",
    lineterm=""
))

print("\n".join(diff) if diff else "No text differences")