import firebase_admin
from firebase_admin import credentials


def initialize_firebase():
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://apphijay-default-rtdb.europe-west1.firebasedatabase.app/'
    })


