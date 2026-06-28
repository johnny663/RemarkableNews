import json
import os

import requests
from dotenv import load_dotenv

from onedrive_client import GRAPH_BASE, get_access_token

load_dotenv()
token = get_access_token(os.environ["AZURE_CLIENT_ID"])
headers = {"Authorization": f"Bearer {token}"}

# 1. Quota numbers + state
drive = requests.get(f"{GRAPH_BASE}/me/drive", headers=headers, timeout=15).json()
quota = drive.get("quota", {})
gb = 1024 ** 3
print("=== QUOTA ===")
print(f"Drive type: {drive.get('driveType')}")
print(f"Total:     {quota.get('total', 0) / gb:.3f} GB")
print(f"Used:      {quota.get('used', 0) / gb:.3f} GB")
print(f"Remaining: {quota.get('remaining', 0) / gb:.3f} GB")
print(f"State:     {quota.get('state')}")

# 2. Tiny test upload — print the FULL error body Graph returns
print("\n=== TEST UPLOAD ===")
url = f"{GRAPH_BASE}/me/drive/root:/reMarkableNews/_test.txt:/content"
resp = requests.put(
    url,
    headers={**headers, "Content-Type": "text/plain"},
    data=b"hello",
    timeout=30,
)
print(f"Status: {resp.status_code}")
print("Body:")
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)
