## SmartDesk API

FastAPI backend with MongoDB persistence and JWT authentication.

### Setup

Create a `.env` file in the project root:

```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>/?retryWrites=true&w=majority
MONGO_DB=smartdesk
SECRET_KEY=replace-with-a-random-secret-at-least-32-characters-long
ALGORITHM=HS256
TOKEN_EXPIRE_MINUTES=30
```

Add your current IP address to the MongoDB Atlas Network Access list. Then install dependencies and start the API:

```powershell
uv sync
uv run uvicorn main:app --reload
```

### Endpoints

- `POST /api/v1/users/register` creates a normal user.
- `POST /api/v1/users/login` returns a bearer token.
- `GET /api/v1/users/me` returns the authenticated user's profile.
- `GET /docs` opens the interactive API documentation.

Public registration cannot create a superuser. Create administrative users through a protected administrative workflow when that feature is added.

### Tests

```powershell
uv run pytest
```
