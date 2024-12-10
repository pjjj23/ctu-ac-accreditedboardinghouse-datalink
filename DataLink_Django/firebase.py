import pyrebase
from firebase_admin import credentials, initialize_app

# Pyrebase Configuration
firebaseConfig = {
    "apiKey": "AIzaSyAfCuib-Q7FmAlr9oj9CIwBONeMkWnpdgU",
    "authDomain": "ctuacaccreditedboardinghouse.firebaseapp.com",
    "databaseURL": "https://ctuacaccreditedboardinghouse-default-rtdb.firebaseio.com",
    "projectId": "ctuacaccreditedboardinghouse",
    "storageBucket": "ctuacaccreditedboardinghouse.appspot.com",
    "messagingSenderId": "930916912489",
    "appId": "1:930916912489:web:58f4a20a4ca620471c81f8",
    "measurementId": "G-2KK40DYS31"
}

# Initialize Pyrebase
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()
auth_instance = firebase.auth()
storage = firebase.storage()  # Initialize Firebase Storage

# Path to the Firebase Admin SDK service account key file
service_account_path = 'C:/Users/Administrator/Desktop/DjangoCapstone/djangoData/FrontEnd_Django/ctuacaccreditedboardinghouse-firebase-adminsdk-f2r9o-1727478a48.json'

# Initialize Firebase Admin SDK
cred = credentials.Certificate(service_account_path)
initialize_app(cred, {
    'databaseURL': 'https://ctuacaccreditedboardinghouse-default-rtdb.firebaseio.com'  # Admin SDK should have access to your Realtime Database
})