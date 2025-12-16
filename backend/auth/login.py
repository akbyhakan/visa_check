"""
VFS Global Login Handler
Handles authentication and navigation for VFS Global visa appointment system.
"""

import time
import logging
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class LoginHandler:
    """
    Handles VFS Global login operations including Cloudflare bypass,
    authentication, and navigation.
    """

    def __init__(self, driver, config: dict):
        """
        Initialize the LoginHandler.

        Args:
            driver: Selenium WebDriver instance
            config: Configuration dictionary containing credentials and settings
        """
        self.driver = driver
        self.config = config
        self.base_url = config.get('base_url', 'https://visa.vfsglobal.com')
        self.username = config.get('username')
        self.password = config.get('password')
        self.timeout = config.get('timeout', 30)
        self.spinner_timeout = config.get('spinner_timeout', 60)

    def wait_for_spinner(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for loading spinner to disappear.

        Args:
            timeout: Maximum time to wait for spinner (default: spinner_timeout from config)

        Returns:
            bool: True if spinner disappeared, False if timeout occurred
        """
        timeout = timeout or self.spinner_timeout
        spinner_selectors = [
            ".spinner",
            ".loading-spinner",
            ".loader",
            "[class*='spinner']",
            "[class*='loading']",
            ".mat-progress-spinner",
            ".ngx-spinner"
        ]

        logger.info("Waiting for spinner to disappear...")

        try:
            for selector in spinner_selectors:
                try:
                    spinner = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if spinner.is_displayed():
                        WebDriverWait(self.driver, timeout).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"Spinner '{selector}' disappeared")
                except NoSuchElementException:
                    continue

            # Additional wait for any AJAX requests to complete
            time.sleep(1)
            return True

        except TimeoutException:
            logger.warning(f"Spinner did not disappear within {timeout} seconds")
            return False

    def handle_cloudflare(self, max_retries: int = 3) -> bool:
        """
        Handle Cloudflare challenge/protection page.

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if Cloudflare challenge was bypassed successfully
        """
        logger.info("Checking for Cloudflare challenge...")

        cloudflare_indicators = [
            "cf-browser-verification",
            "cf_challenge",
            "cloudflare",
            "challenge-running",
            "ray-id"
        ]

        for attempt in range(max_retries):
            try:
                page_source = self.driver.page_source.lower()

                # Check if Cloudflare challenge is present
                is_cloudflare = any(indicator in page_source for indicator in cloudflare_indicators)

                if not is_cloudflare:
                    logger.info("No Cloudflare challenge detected")
                    return True

                logger.info(f"Cloudflare challenge detected, attempt {attempt + 1}/{max_retries}")

                # Wait for Cloudflare challenge to resolve
                # Look for the checkbox or automatic bypass
                try:
                    # Try to find and click the Cloudflare checkbox if present
                    cf_checkbox = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']"))
                    )
                    cf_checkbox.click()
                    logger.info("Clicked Cloudflare checkbox")
                except (TimeoutException, NoSuchElementException):
                    pass

                # Wait for challenge to complete
                WebDriverWait(self.driver, 30).until(
                    lambda d: not any(ind in d.page_source.lower() for ind in cloudflare_indicators)
                )

                logger.info("Cloudflare challenge bypassed successfully")
                return True

            except TimeoutException:
                logger.warning(f"Cloudflare bypass attempt {attempt + 1} failed")
                time.sleep(5)

        logger.error("Failed to bypass Cloudflare challenge after all retries")
        return False

    def login(self) -> bool:
        """
        Perform login to VFS Global portal.

        Returns:
            bool: True if login was successful, False otherwise
        """
        logger.info("Starting login process...")

        try:
            # Navigate to login page
            login_url = f"{self.base_url}/login"
            self.driver.get(login_url)

            # Handle Cloudflare if present
            if not self.handle_cloudflare():
                logger.error("Failed to handle Cloudflare challenge")
                return False

            # Wait for page to load
            self.wait_for_spinner()

            # Wait for login form to be present
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form, [class*='login']"))
            )

            # Find and fill username field
            username_selectors = [
                "input[type='email']",
                "input[name='username']",
                "input[name='email']",
                "#username",
                "#email"
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not username_field:
                logger.error("Could not find username field")
                return False

            username_field.clear()
            username_field.send_keys(self.username)
            logger.info("Entered username")

            # Find and fill password field
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "#password"
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not password_field:
                logger.error("Could not find password field")
                return False

            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Entered password")

            # Find and click login button
            login_button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[class*='login']",
                ".btn-login",
                "#loginButton"
            ]

            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not login_button:
                logger.error("Could not find login button")
                return False

            login_button.click()
            logger.info("Clicked login button")

            # Wait for spinner and page transition
            self.wait_for_spinner()

            # Verify login success by checking for dashboard or user elements
            success_indicators = [
                "[class*='dashboard']",
                "[class*='user-profile']",
                "[class*='logout']",
                "[class*='appointments']"
            ]

            for indicator in success_indicators:
                try:
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                    )
                    logger.info("Login successful!")
                    return True
                except TimeoutException:
                    continue

            # Check for error messages
            error_selectors = [
                ".error-message",
                ".alert-danger",
                "[class*='error']"
            ]

            for selector in error_selectors:
                try:
                    error = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if error.is_displayed():
                        logger.error(f"Login failed: {error.text}")
                        return False
                except NoSuchElementException:
                    continue

            logger.warning("Login status uncertain, proceeding cautiously")
            return True

        except Exception as e:
            logger.error(f"Login failed with exception: {str(e)}")
            return False

    def logout(self) -> bool:
        """
        Perform logout from VFS Global portal.

        Returns:
            bool: True if logout was successful, False otherwise
        """
        logger.info("Starting logout process...")

        try:
            logout_selectors = [
                "a[href*='logout']",
                "button[class*='logout']",
                ".logout-btn",
                "#logoutButton",
                "[class*='sign-out']"
            ]

            logout_element = None
            for selector in logout_selectors:
                try:
                    logout_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not logout_element:
                # Try finding logout in dropdown menu
                try:
                    user_menu = self.driver.find_element(
                        By.CSS_SELECTOR, "[class*='user-menu'], [class*='profile-dropdown']"
                    )
                    user_menu.click()
                    time.sleep(1)

                    for selector in logout_selectors:
                        try:
                            logout_element = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            break
                        except TimeoutException:
                            continue
                except NoSuchElementException:
                    pass

            if not logout_element:
                logger.error("Could not find logout button")
                return False

            logout_element.click()
            logger.info("Clicked logout button")

            # Wait for logout to complete
            self.wait_for_spinner()

            # Verify logout by checking for login page elements
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[type='password']"))
                )
                logger.info("Logout successful!")
                return True
            except TimeoutException:
                logger.warning("Could not verify logout completion")
                return True

        except Exception as e:
            logger.error(f"Logout failed with exception: {str(e)}")
            return False

    def navigate_to_new_booking(self) -> bool:
        """
        Navigate to new appointment booking page.

        Returns:
            bool: True if navigation was successful, False otherwise
        """
        logger.info("Navigating to new booking page...")

        try:
            # Wait for any spinners to complete
            self.wait_for_spinner()

            booking_selectors = [
                "a[href*='new-booking']",
                "a[href*='appointment']",
                "a[href*='schedule']",
                "button[class*='new-booking']",
                "[class*='book-appointment']",
                ".new-booking-btn",
                "#newBookingButton"
            ]

            booking_element = None
            for selector in booking_selectors:
                try:
                    booking_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not booking_element:
                # Try direct navigation
                booking_url = f"{self.base_url}/new-booking"
                self.driver.get(booking_url)

                if not self.handle_cloudflare():
                    logger.error("Failed to handle Cloudflare during navigation")
                    return False

                self.wait_for_spinner()
                logger.info("Navigated to new booking page via direct URL")
                return True

            booking_element.click()
            logger.info("Clicked new booking button")

            # Wait for page to load
            self.wait_for_spinner()

            # Verify navigation success
            booking_page_indicators = [
                "[class*='booking-form']",
                "[class*='appointment-form']",
                "[class*='visa-category']",
                "select[name*='category']"
            ]

            for indicator in booking_page_indicators:
                try:
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                    )
                    logger.info("Successfully navigated to new booking page!")
                    return True
                except TimeoutException:
                    continue

            logger.warning("Navigation completed but could not verify booking page")
            return True

        except Exception as e:
            logger.error(f"Navigation to new booking failed: {str(e)}")
            return False
