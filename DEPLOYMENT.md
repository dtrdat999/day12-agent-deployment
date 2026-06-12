# Deployment Information

## Public URL
https://[ten-app-cua-ban].onrender.com (Hoặc railway.app)

## Platform
Render / Railway

## Test Commands

### Health Check
```bash
curl https://[ten-app-cua-ban].onrender.com/health
# Expected: {"status": "ok"}
```

### API Test (with authentication)
```bash
curl -X POST https://[ten-app-cua-ban].onrender.com/ask \
  -H "X-API-Key: [API_KEY_CUA_BAN]" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set
- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)
