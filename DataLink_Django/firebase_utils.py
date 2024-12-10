from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from django.conf import settings  # Import Django settings

# Dynamically build the path using BASE_DIR and Pathlib
FIREBASE_CREDENTIALS_PATH = Path(settings.BASE_DIR) / 'djangoData' / 'FrontEnd_Django' / 'ctuacaccreditedboardinghouse-firebase-adminsdk-f2r9o-1727478a48.json'

def initialize_firebase():
    if not firebase_admin._apps:  # Check if Firebase has already been initialized
        cred = credentials.Certificate(str(FIREBASE_CREDENTIALS_PATH))
        firebase_admin.initialize_app(cred)
