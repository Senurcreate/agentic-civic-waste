import toml
import httpx

secrets = toml.load("secrets.toml")

SUPABASE_URL = secrets["SUPABASE_URL"]
SUPABASE_KEY = secrets["SUPABASE_KEY"]

bucket = "waste-images"
path = "tests/test-image-2.jpg"

upload_url = (
    f"{SUPABASE_URL}/storage/v1/object/"
    f"{bucket}/{path}"
)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "image/jpeg"
}

with open("assets/hero.png", "rb") as f:
    image_bytes = f.read()

response = httpx.post(
    upload_url,
    headers=headers,
    content=image_bytes,
    timeout=30
)

print("STATUS:", response.status_code)
print("BODY:", response.text)