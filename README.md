# AI Help Center Backend

FastAPI-based backend for the AI Help Center application with MongoDB integration.

## Features

- RESTful API endpoints
- WebSocket support for real-time chat
- JWT authentication
- Role-based access control
- MongoDB integration
- AI-powered chat responses using Ollama
- File upload handling
- Error tracking and logging

## Tech Stack

- Python 3.8+
- FastAPI
- MongoDB (Motor)
- Ollama
- JWT Authentication
- WebSockets
- Pydantic

## Getting Started

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

## Deployment

1. Push to GitHub
2. Deploy to Vercel:
```bash
vercel
```

## Environment Variables

Required environment variables:
- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `SECRET_KEY`: JWT secret key
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration
- `CORS_ORIGINS`: Allowed origins for CORS

## API Documentation

Once the server is running, visit:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Default Admin Account

- Email: admin@example.com
- Password: admin123 