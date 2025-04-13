# AI Help Center Backend

FastAPI-based backend for the AI Help Center application with MongoDB integration.

## Features

- RESTful API endpoints
- WebSocket support for real-time chat
- JWT authentication
- Role-based access control
- MongoDB integration
- AI-powered chat responses
- File upload handling
- Error tracking and logging

## Tech Stack

- Python 3.11
- FastAPI
- MongoDB (Motor)
- JWT Authentication
- WebSockets
- Pydantic

## Production Deployment (Render)

1. Make sure your code is pushed to GitHub
2. Go to [Render.com](https://render.com) and sign in
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - Name: ai-help-center-backend
   - Environment: Python 3
   - Region: Choose nearest to your users
   - Branch: main
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host=0.0.0.0 --port=$PORT`
6. Add environment variables from `.env.production`
7. Click "Create Web Service"

The service will be deployed at: `https://your-service-name.onrender.com`

## Local Development

1. Clone the repository:
```bash
git clone <your-backend-repo-url>
cd ai-help-center-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=ai_assistance
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=["http://localhost:3000"]
```

5. Start the server:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Environment Variables

Required environment variables:
- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `SECRET_KEY`: JWT secret key
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration
- `CORS_ORIGINS`: Allowed origins for CORS

## Project Structure
```
backend/
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── Procfile            # Render deployment configuration
├── render.yaml         # Render service configuration
├── runtime.txt         # Python version specification
├── .env.production     # Production environment variables
├── core/              # Core functionality
├── models/            # Pydantic models
├── routers/           # API routes
└── services/          # Business logic
```

## Default Admin Account

- Email: admin@example.com
- Password: admin123 