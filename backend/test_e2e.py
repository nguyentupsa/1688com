#!/usr/bin/env python3
"""
End-to-end test for the 1688 Negotiation Agent system.
This test verifies the basic functionality without requiring actual 1688 login.
"""

import asyncio
import json
import logging
import os
import sys

import pytest
from playwright.async_api import async_playwright

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings import settings
from playwright_driver import PlaywrightDriver
from ai_client import ai_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Test1688NegotiationAgent:
    """Test suite for the 1688 Negotiation Agent."""

    @pytest.fixture
    async def driver(self):
        """Create a playwright driver for testing."""
        driver = PlaywrightDriver()
        await driver.start()
        yield driver
        await driver.stop()

    @pytest.fixture
    def test_config(self):
        """Test configuration."""
        return {
            "product_url": "https://detail.1688.com/offer/123456789.html",  # Test URL
            "opening_template": "你好，我想了解这款产品。",
            "goals": {
                "target_price": "100元",
                "moq": "100件",
                "lead_time": "15天"
            },
            "max_turns": 2,
            "wait_timeout_s": 10,  # Short timeout for testing
            "locale": "zh"
        }

    @pytest.mark.asyncio
    async def test_browser_initialization(self):
        """Test that the browser can be initialized properly."""
        driver = PlaywrightDriver()
        try:
            await driver.start()
            assert driver.browser is not None
            assert driver.context is not None
            assert driver.page is not None
            logger.info(" Browser initialization test passed")
        finally:
            await driver.stop()

    @pytest.mark.asyncio
    async def test_login_url_navigation(self, driver):
        """Test navigation to the login URL."""
        try:
            # Navigate to login URL
            await driver.page.goto(
                settings.login_url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            # Take screenshot for verification
            screenshot_path = await driver.take_screenshot("test_login_navigation")
            assert os.path.exists(screenshot_path)
            assert screenshot_path.endswith('.png')

            # Check if we're on a taobao/1688 domain
            current_url = driver.page.url
            assert any(domain in current_url for domain in ['taobao.com', '1688.com', 'login.1688.com'])

            logger.info(" Login URL navigation test passed")
        except Exception as e:
            logger.error(f" Login URL navigation test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_ai_client_functionality(self):
        """Test the AI client functionality."""
        try:
            # Test AI client initialization
            assert ai_client is not None

            # Test mock response generation
            history = [
                {"role": "user", "text": "你好，我想了解产品价格"}
            ]
            supplier_text = "我们的价格是100元每件"

            response = await ai_client.generate_next_reply(
                history=history,
                supplier_text=supplier_text,
                goals={},
                product_url="https://detail.1688.com/offer/test.html"
            )

            assert response is not None
            assert "text" in response
            assert "used_model" in response
            assert "is_mock" in response
            assert len(response["text"]) > 0

            logger.info(f" AI client test passed. Response: {response['text'][:50]}...")

        except Exception as e:
            logger.error(f" AI client test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_screenshot_functionality(self, driver):
        """Test screenshot functionality."""
        try:
            # Navigate to a simple page
            await driver.page.goto("https://httpbin.org/html", timeout=30000)

            # Take screenshot
            screenshot_path = await driver.take_screenshot("test_screenshot")

            # Verify screenshot was created
            assert os.path.exists(screenshot_path)
            assert screenshot_path.endswith('.png')

            # Check file size (should be > 0)
            file_size = os.path.getsize(screenshot_path)
            assert file_size > 1000  # Should be at least 1KB

            logger.info(f" Screenshot test passed. File size: {file_size} bytes")

        except Exception as e:
            logger.error(f" Screenshot test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_data_directory_structure(self):
        """Test that required directories exist."""
        try:
            # Check data directory exists
            assert os.path.exists(settings.data_dir)

            # Check user data directory exists (should be created by driver)
            user_data_dir = settings.user_data_dir
            os.makedirs(user_data_dir, exist_ok=True)
            assert os.path.exists(user_data_dir)

            logger.info(" Data directory structure test passed")

        except Exception as e:
            logger.error(f" Data directory structure test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_configuration_values(self):
        """Test that configuration values are properly loaded."""
        try:
            # Test essential settings
            assert settings.login_url is not None
            assert settings.work_1688_url_pattern is not None
            assert settings.data_dir is not None
            assert settings.user_data_dir is not None

            # Test URLs are valid
            assert settings.login_url.startswith('https://')
            assert settings.work_1688_url_pattern.startswith('https://')

            logger.info(" Configuration values test passed")

        except Exception as e:
            logger.error(f" Configuration values test failed: {e}")
            raise

async def run_all_tests():
    """Run all tests manually."""
    logger.info("Starting 1688 Negotiation Agent Tests")

    tests = [
        ("Browser Initialization", Test1688NegotiationAgent().test_browser_initialization()),
        ("AI Client Functionality", Test1688NegotiationAgent().test_ai_client_functionality()),
        ("Data Directory Structure", Test1688NegotiationAgent().test_data_directory_structure()),
        ("Configuration Values", Test1688NegotiationAgent().test_configuration_values()),
    ]

    passed = 0
    failed = 0

    for test_name, test_coro in tests:
        try:
            logger.info(f"Running: {test_name}")
            await test_coro
            passed += 1
            logger.info(f" {test_name} - PASSED")
        except Exception as e:
            failed += 1
            logger.error(f" {test_name} - FAILED: {e}")

    logger.info(f"\nTest Results: {passed} passed, {failed} failed")

    if failed > 0:
        logger.error("Some tests failed!")
        return False
    else:
        logger.info("All tests passed!")
        return True

if __name__ == "__main__":
    # Run tests when script is executed directly
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)