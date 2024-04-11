import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Test:
    def __init__(self):
        self.driver = None
        self.vars = {}
        self.cookies = ""

        # definitions
        self.inclusion = "cohortBuild_cohort_inclusionCriteria"
        self.required = "cohortBuild_cohort_requiredFilter"
        self.exclusion = "cohortBuild_cohort_excludeFilter"
        self.onset = "cohortBuild_cohort_adjustOnsetTime"
        # Locators
        self.NAVBAR_BRAND = (By.CSS_SELECTOR, "a.navbar-brand")
        self.DROPDOWN_CRITERIA = (By.XPATH, ".//div[@role='menuitem']")
        self.CONDITIONS_OPTIONS = (By.CSS_SELECTOR, "div.dropdown---menu-item---1LjoL")
        self.TIME_SCOPE_FROM_INPUT = (By.XPATH, "//input[@type='text'][contains(@class, 'react-datepicker__input-container')][1]")
        self.TIME_SCOPE_TO_INPUT = (By.XPATH, "//input[@type='text'][contains(@class, 'react-datepicker__input-container')][2]")
        self.DEMOGRAPHICS_AGE_SLIDER = (By.CSS_SELECTOR, "div.rc-slider")
        self.COLOR_CASE_MALE = (By.XPATH, "//div[text()='case male:']/following-sibling::div")
        self.COLOR_CASE_FEMALE = (By.XPATH, "//div[text()='case female:']/following-sibling::div")
        self.COHORT_EDITOR = (By.XPATH, "/html/body/div/div/div/main/div[2]/div/div/div/div[1]/div[1]/div[3]/div[2]/div[2]")
        self.cohort_editor_elements = {}

        self.setup_method()

    def setup_method(self, method=None):
        options = Options()
        # options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def teardown_method(self, method=None):
        self.driver.quit()

    def login(self):
        self.driver.get("http://localhost:5050/")
        print(self.driver.title)
        # print(self.driver.current_url)
        self.driver.maximize_window()
        WebDriverWait(self.driver, timeout=100).until(lambda d: d.find_element(By.NAME, "username"))
        self.driver.find_element(By.NAME, "username").click()
        self.driver.find_element(By.NAME, "username").send_keys("maya")

        self.driver.find_element(By.NAME, "password").click()
        self.driver.find_element(By.NAME, "password").send_keys("mayah")
        self.driver.find_element(By.XPATH, "//button[contains(.,'Login')]").click()

        # print(self.driver.current_url)
        # Wait for the authentication to complete
        WebDriverWait(self.driver, timeout=10).until(lambda d: d.find_element(By.XPATH, "//a[contains(text(),'Cohort Builder')]"))

    def open_cohort_builder(self):
        element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//a[contains(text(),'Cohort Builder')]"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()

    # Methods for interaction
    def click_reset(self):
        self.driver.find_element(By.CSS_SELECTOR, ".btn-danger").click()

    def get_page_title(self):
        return self.driver.title

    def click_navbar_button(self, text):
        NAVBAR_BUTTON = (
            By.XPATH,
            f"//*[@id='outer-container']/div/nav/div/ul/li//button[contains(normalize-space(.), '{text}')]",
        )
        button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(NAVBAR_BUTTON))
        button.click()

    def identify_cohort_cards(self):
        elements = self.driver.find_element(*self.COHORT_EDITOR)
        for element in elements.find_elements(By.XPATH, ".//div[@class='card-body']"):
            name = element.get_attribute("id")
            drop_button = element.find_element(By.XPATH, "..").find_element(By.XPATH, ".//button[@type='button']")
            self.cohort_editor_elements[name] = drop_button

    def select_criteria(self, condition, criteria):
        self.cohort_editor_elements[condition].click()
        option = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, f".//div[@role='menuitem'][contains(text(), '{criteria}')]"))
        )
        option.click()
        self.driver.find_element(By.XPATH, "//*[@id='generic_trigger']/ul/li/input").click()

    def set_time_scope(self, from_date, to_date):
        from_input = self.driver.find_element(*self.TIME_SCOPE_FROM_INPUT)
        to_input = self.driver.find_element(*self.TIME_SCOPE_TO_INPUT)
        from_input.clear()
        from_input.send_keys(from_date)
        to_input.clear()
        to_input.send_keys(to_date)

    def start_with_login(self):
        self.login()
        print(self.driver.current_url)
        self.open_cohort_builder()
        print(self.driver.current_url)
        self.identify_cohort_cards()
        # self.click_navbar_button("Load")


t = Test()
t.start_with_login()
t.select_criteria("cohortBuild_cohort_inclusionCriteria", "ICD9")
time.sleep(5)
