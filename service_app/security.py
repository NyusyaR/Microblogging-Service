from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="api-key", auto_error=True)
