import firebase_admin
from firebase_admin import credentials, storage
import os, json
from urllib.parse import urlparse, unquote


# === Firebase Initialization ===
if not firebase_admin._apps:
    creds_raw = os.environ.get('FIREBASE_CREDENTIALS_JSON')
    if not creds_raw:
        raise Exception("Firebase credentials not found in env")

    cred_dict = json.loads(creds_raw)
    cred = credentials.Certificate(cred_dict)

    firebase_admin.initialize_app(cred, {
        'storageBucket': 'cu-hr-caf00.firebasestorage.app'
    })

bucket = storage.bucket()
print("🔥 Firebase initialized with bucket:", bucket.name)


# === Upload Function ===
def upload_file_to_firebase(file_path, destination_blob_name, make_public=True):
    """
    Uploads a local file to Firebase Storage.
    
    :param file_path: Local path to the file (e.g. 'media/test.jpg')
    :param destination_blob_name: Path in Firebase (e.g. 'uploads/test.jpg')
    :param make_public: If True, makes the uploaded file publicly accessible
    :return: Public URL of the file (if public), else None
    """
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    
    if make_public:
        blob.make_public()
        return blob.public_url
    return None



def delete_file_from_firebase(public_url):
    """
    Deletes a file from Firebase Storage using its public URL.
    """
    bucket = storage.bucket()

    # Extract the path from the URL
    path = urlparse(public_url).path.lstrip('/')

    # Remove the bucket name if it's in the path
    if path.startswith(bucket.name + "/"):
        path = path[len(bucket.name) + 1:]

    # Decode URL-encoded characters like %20
    path = unquote(path)

    try:
        blob = bucket.blob(path)
        if blob.exists():
            blob.delete()
            print(f"🔥 Deleted file from Firebase: {path}")
        else:
            print(f"⚠️ File not found in Firebase: {path}")
    except Exception as e:
        print(f"❌ Failed to delete file from Firebase: {path}")
        print(f"Error: {str(e)}")