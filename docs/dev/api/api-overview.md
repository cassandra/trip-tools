# API Domain

## API Token Glossary

| Concept | Name | Description |
|---------|------|-------------|
| `tt_` | (literal) | Fixed app identifier for trip-tools tokens |
| `lookup_key` | model field, variable | 8 random chars for fast DB lookup |
| `secret_key` | variable only | 40 random chars for auth (never stored) |
| `api_token_str` | variable | Full token string: `tt_{lookup_key}_{secret_key}` |
| `APIToken` | model class | Database record |
| `api_token` | variable | Instance of APIToken model |
| `api_token_hash` | model field | SHA256 hash of `api_token_str` |

## Token Format

```
tt_{lookup_key}_{secret_key}
```

- `tt_`: Fixed prefix identifying this as a trip-tools token
- `lookup_key`: 8 URL-safe random characters for fast database lookup (stored in plain text)
- `secret_key`: 40 URL-safe random characters for authentication (only hash stored)

The `lookup_key` and `secret_key` are generated independently, so the stored `lookup_key` reveals nothing about the secret portion.

## Authentication Flow

1. User sends `Authorization: Bearer tt_{lookup_key}_{secret_key}` header
2. `APITokenDRFAuthAdapter` extracts the `api_token_str` from the header
3. `APITokenService.authenticate()` parses out the `lookup_key`
4. Database lookup by `lookup_key` (indexed for fast retrieval)
5. SHA256 hash of full `api_token_str` compared against stored `api_token_hash`
6. Constant-time comparison prevents timing attacks
7. On match, `last_used_at` timestamp updated and user returned
