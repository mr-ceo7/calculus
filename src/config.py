"""
Configuration module for Smart Notes Generator
Supports environment-based configuration for development and production
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Base configuration with sensible defaults"""
    
    # Base directory of the application
    BASE_DIR: Path = Path(__file__).parent.absolute()
    
    # Flask configuration
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING: bool = False
    
    # Upload configuration
    UPLOAD_FOLDER: Path = BASE_DIR / 'uploads'
    OUTPUT_FOLDER: Path = BASE_DIR / 'outputs'
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: set = frozenset({'pdf', 'txt'})
    
    # Converter configuration
    TEMPLATE_PATH: Path = BASE_DIR / 'converter' / 'smart_template.html'

    # Gemini configuration
    # Temporary hardcoded key for local testing (replace/remove in production)
    GEMINI_API_KEY: str = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_PREFERRED_MODEL: str = os.environ.get('GEMINI_PREFERRED_MODEL', 'gemini-2.5-flash')
    GEMINI_FALLBACK_MODEL: str = os.environ.get('GEMINI_FALLBACK_MODEL', 'gemini-2.0-flash')
    GEMINI_TIMEOUT_SECONDS: float = float(os.environ.get('GEMINI_TIMEOUT_SECONDS', '240'))
    # Increased to 32K - maximum for gemini-2.5-flash
    GEMINI_MAX_OUTPUT_TOKENS: int = int(os.environ.get('GEMINI_MAX_OUTPUT_TOKENS', '32768'))
    
    def __post_init__(self):
        """Validate and create necessary directories"""
        # Compute GEMINI_ENABLED after GEMINI_API_KEY is set
        object.__setattr__(self, 'GEMINI_ENABLED', bool(self.GEMINI_API_KEY))
    
    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[Path] = None
    
    def __post_init__(self):
        """Validate and create necessary directories"""
        # Compute GEMINI_ENABLED after GEMINI_API_KEY is set
        object.__setattr__(self, 'GEMINI_ENABLED', bool(self.GEMINI_API_KEY))
        
        # Ensure directories exist
        self.UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
        self.OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)
        
        # Validate template exists
        if not self.TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Template not found: {self.TEMPLATE_PATH}")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls()


@dataclass
class DevelopmentConfig(Config):
    """Development configuration with debug enabled"""
    DEBUG: bool = True
    LOG_LEVEL: str = 'DEBUG'


@dataclass
class ProductionConfig(Config):
    """Production configuration with strict settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = 'WARNING'
    
    def __post_init__(self):
        super().__post_init__()
        # Production must have a real secret key
        if self.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY must be set in production environment")


@dataclass
class TestingConfig(Config):
    """Testing configuration with temp directories"""
    TESTING: bool = True
    DEBUG: bool = True
    LOG_LEVEL: str = 'DEBUG'
    
    # Use temp directories for testing
    UPLOAD_FOLDER: Path = Path('/tmp/smart_notes_test/uploads')
    OUTPUT_FOLDER: Path = Path('/tmp/smart_notes_test/outputs')


# Configuration factory
def get_config(env: Optional[str] = None) -> Config:
    """
    Get configuration based on environment
    
    Args:
        env: Environment name ('development', 'production', 'testing')
             If None, reads from FLASK_ENV environment variable
    
    Returns:
        Configuration instance
    """
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }
    
    config_class = configs.get(env.lower(), DevelopmentConfig)
    return config_class.from_env()
