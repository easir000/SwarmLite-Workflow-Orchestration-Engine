import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to manage environment variables"""
    
    # Database Configuration
    DB_ENCRYPTION_KEY: str = os.getenv("DB_ENCRYPTION_KEY", "")
    AUDIT_SECRET_KEY: str = os.getenv("AUDIT_SECRET_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///swarmlite.db")
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    
    # Server Configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Governance Configuration
    GOVERNANCE_CONFIG_PATH: str = os.getenv("GOVERNANCE_CONFIG_PATH", "config/governance.yaml")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    @classmethod
    def validate_required_keys(cls):
        """Validate that required environment variables are set"""
        required_keys = ["AUDIT_SECRET_KEY"]
        missing_keys = []
        
        for key in required_keys:
            value = getattr(cls, key)
            if not value:
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        # Validate key lengths
        if len(cls.AUDIT_SECRET_KEY) < 32:
            raise ValueError("AUDIT_SECRET_KEY must be at least 32 characters long")
        
        if cls.DB_ENCRYPTION_KEY and len(cls.DB_ENCRYPTION_KEY) < 32:
            raise ValueError("DB_ENCRYPTION_KEY must be at least 32 characters long")