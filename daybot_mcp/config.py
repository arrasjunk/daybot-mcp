"""
Configuration management for DayBot MCP.
Loads environment variables and provides configuration settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Alpaca API Configuration
    alpaca_api_key: str = Field(..., env="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(..., env="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        env="ALPACA_BASE_URL"
    )
    
    # Risk Management Settings
    max_position_size: float = Field(default=0.02, env="MAX_POSITION_SIZE")  # 2% of portfolio
    max_daily_loss: float = Field(default=0.05, env="MAX_DAILY_LOSS")  # 5% daily loss limit
    default_stop_loss: float = Field(default=0.02, env="DEFAULT_STOP_LOSS")  # 2% stop loss
    default_take_profit: float = Field(default=0.04, env="DEFAULT_TAKE_PROFIT")  # 4% take profit
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    
    # Trading Configuration
    market_open_buffer: int = Field(default=5, env="MARKET_OPEN_BUFFER")  # minutes after market open
    market_close_buffer: int = Field(default=15, env="MARKET_CLOSE_BUFFER")  # minutes before market close
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_alpaca_headers() -> dict:
    """Get headers for Alpaca API requests."""
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        "Content-Type": "application/json"
    }


def validate_config() -> bool:
    """Validate that all required configuration is present."""
    try:
        # Check required Alpaca credentials
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            return False
        
        # Validate risk parameters
        if settings.max_position_size <= 0 or settings.max_position_size > 1:
            return False
            
        if settings.max_daily_loss <= 0 or settings.max_daily_loss > 1:
            return False
            
        return True
    except Exception:
        return False
