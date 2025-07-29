import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/codepilot")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # AI API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # File Upload
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php"}
    
    # Git
    TEMP_DIR = "temp_repos"
    
    # App Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_CALLS = 100
    RATE_LIMIT_PERIOD = 3600  # 1 hour