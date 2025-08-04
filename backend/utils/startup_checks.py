"""
Startup checks for BT-RADS system
Verifies that required services are available
"""
import os
import asyncio
import logging
import aiohttp
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class StartupChecker:
    """Performs startup checks for the system"""
    
    def __init__(self):
        self.checks_passed = {}
        self.warnings = []
        self.errors = []
    
    async def check_vllm_service(self) -> bool:
        """Check if vLLM service is available"""
        vllm_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{vllm_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info("✅ vLLM service is available")
                        self.checks_passed["vllm"] = True
                        return True
                    else:
                        logger.warning(f"⚠️  vLLM service returned status {response.status}")
                        self.warnings.append("vLLM service is not healthy")
                        return False
        except Exception as e:
            logger.error(f"❌ vLLM service not available: {e}")
            self.errors.append(f"Cannot connect to vLLM at {vllm_url}")
            self.checks_passed["vllm"] = False
            return False
    
    async def check_ollama_service(self) -> bool:
        """Check if Ollama service is available"""
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        logger.info(f"✅ Ollama service is available with {len(models)} models")
                        self.checks_passed["ollama"] = True
                        return True
                    else:
                        logger.warning(f"⚠️  Ollama service returned status {response.status}")
                        self.warnings.append("Ollama service is not healthy")
                        return False
        except Exception as e:
            logger.error(f"❌ Ollama service not available: {e}")
            self.errors.append(f"Cannot connect to Ollama at {ollama_url}")
            self.checks_passed["ollama"] = False
            return False
    
    async def check_redis(self) -> bool:
        """Check if Redis is available"""
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        try:
            r = redis.from_url(redis_url, decode_responses=True)
            await r.ping()
            await r.close()
            logger.info("✅ Redis is available")
            self.checks_passed["redis"] = True
            return True
        except Exception as e:
            logger.error(f"❌ Redis not available: {e}")
            self.errors.append(f"Cannot connect to Redis at {redis_url}")
            self.checks_passed["redis"] = False
            return False
    
    async def check_database(self) -> bool:
        """Check if PostgreSQL is available"""
        import asyncpg
        
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/btrads_db")
        
        try:
            conn = await asyncpg.connect(db_url)
            await conn.fetchval("SELECT 1")
            await conn.close()
            logger.info("✅ PostgreSQL is available")
            self.checks_passed["postgres"] = True
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL not available: {e}")
            self.errors.append(f"Cannot connect to database: {e}")
            self.checks_passed["postgres"] = False
            return False
    
    async def determine_agent_mode(self) -> str:
        """Determine which agent mode to use based on available services"""
        requested_mode = os.getenv("AGENT_MODE", "vllm")
        
        # Check requested mode first
        if requested_mode == "vllm" and self.checks_passed.get("vllm"):
            return "vllm"
        elif requested_mode == "ollama" and self.checks_passed.get("ollama"):
            return "ollama"
        elif requested_mode == "mock":
            return "mock"
        
        # Fallback logic
        if self.checks_passed.get("vllm"):
            logger.info("Using vLLM mode (fallback)")
            return "vllm"
        elif self.checks_passed.get("ollama"):
            logger.info("Using Ollama mode (fallback)")
            return "ollama"
        else:
            logger.warning("⚠️  No LLM services available, using mock mode")
            self.warnings.append("Running in mock mode - no LLM services available")
            return "mock"
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all startup checks"""
        logger.info("Running startup checks...")
        logger.info("=" * 50)
        
        # Run checks in parallel
        results = await asyncio.gather(
            self.check_vllm_service(),
            self.check_ollama_service(),
            self.check_redis(),
            self.check_database(),
            return_exceptions=True
        )
        
        # Determine agent mode
        agent_mode = await self.determine_agent_mode()
        
        # Update environment variable
        os.environ["AGENT_MODE"] = agent_mode
        
        # Summary
        logger.info("=" * 50)
        logger.info("Startup Check Summary:")
        logger.info(f"  Agent Mode: {agent_mode}")
        logger.info(f"  Services: {self.checks_passed}")
        
        if self.warnings:
            logger.warning("  Warnings:")
            for warning in self.warnings:
                logger.warning(f"    - {warning}")
        
        if self.errors:
            logger.error("  Errors:")
            for error in self.errors:
                logger.error(f"    - {error}")
        
        logger.info("=" * 50)
        
        return {
            "agent_mode": agent_mode,
            "checks_passed": self.checks_passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "all_required_passed": self.checks_passed.get("redis", False) and 
                                  self.checks_passed.get("postgres", False)
        }

# Run startup checks
async def run_startup_checks() -> Dict[str, Any]:
    """Run all startup checks and return results"""
    checker = StartupChecker()
    return await checker.run_all_checks()