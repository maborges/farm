from jose import jwt
from core.config import settings
from datetime import datetime, timedelta

tenant_id = "74b78031-2c24-4678-b135-e18d2b2c2be0"
user_id = "00000000-0000-0000-0000-000000000001"

payload = {
    "tenant_id": tenant_id,
    "sub": user_id,
    "exp": datetime.utcnow() + timedelta(days=1)
}

token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
print(token)
