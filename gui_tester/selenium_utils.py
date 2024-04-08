from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ORIGIN = "http://localhost:5050/"


def driver_setup():
    """
    Sets up a headless Chrome WebDriver.
    Returns:
        A WebDriver instance with a 10-second implicit wait.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver


def login():
    """
    Logs into the application using hardcoded credentials (maya's user).
    Returns:
        A WebDriver instance after successful login.
    """
    driver = driver_setup()
    driver.get(ORIGIN)

    # print(self.driver.current_url)
    driver.maximize_window()

    WebDriverWait(driver, timeout=100).until(lambda d: d.find_element(By.NAME, "username"))
    driver.find_element(By.NAME, "username").click()
    driver.find_element(By.NAME, "username").send_keys("maya")

    driver.find_element(By.NAME, "password").click()
    driver.find_element(By.NAME, "password").send_keys("mayah")
    driver.find_element(By.XPATH, "//button[contains(.,'Login')]").click()

    # print(driver.current_url)
    # Wait for the authentication to complete
    WebDriverWait(driver, timeout=10).until(lambda d: d.find_element(By.XPATH, "//a[contains(text(),'Cohort Builder')]"))

    print(driver.title)

    return driver
