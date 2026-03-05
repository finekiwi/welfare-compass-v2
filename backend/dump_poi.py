import os
import django
import sys

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from policies.models import MapPOI

poi = MapPOI.objects.last()
if poi:
    with open('poi_dump.txt', 'w', encoding='utf-8') as f:
        f.write(str(poi.original_data))
