import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class Test:
    def __init__(self):
        self.driver = None

        # definitions
        self.conditions = {
            "inclusion": "cohortBuild_cohort_inclusionCriteria",
            "required": "cohortBuild_cohort_requiredFilter",
            "exclusion": "cohortBuild_cohort_excludeFilter",
            "onset": "cohortBuild_cohort_adjustOnsetTime",
        }
        # Locators
        self.COHORT_BUILDER_LINK = (By.XPATH, "//a[contains(text(),'Cohort Builder')]")
        self.NAVBAR_BRAND = (By.CSS_SELECTOR, "a.navbar-brand")
        self.DROPDOWN_CRITERIA = (By.XPATH, ".//div[@role='menuitem']")
        self.DROPDOWN_LOCATOR = (By.XPATH, "//*[@id='generic_trigger']/ul/li/input")
        self.CONDITIONS_OPTIONS = (By.CSS_SELECTOR, "div.dropdown---menu-item---1LjoL")
        self.TIME_SCOPE_FROM_INPUT = (By.XPATH, "//input[@type='text'][contains(@class, 'react-datepicker__input-container')][1]")
        self.TIME_SCOPE_TO_INPUT = (By.XPATH, "//input[@type='text'][contains(@class, 'react-datepicker__input-container')][2]")
        self.DEMOGRAPHICS_AGE_SLIDER = (By.CSS_SELECTOR, "div.rc-slider")
        self.COHORT_EDITOR = (By.XPATH, "/html/body/div/div/div/main/div[2]/div/div/div/div[1]/div[1]/div[3]/div[2]/div[2]")
        self.START_TIME_LOCATOR = (By.ID, "timeWindowStime")
        self.END_TIME_LOCATOR = (By.ID, "timeWindowEtime")
        self.NEGATE_LOCATOR = (By.ID, "negate")
        self.cohort_editor_elements = {}

        self.setup_method()

    def setup_method(self, method=None):
        options = Options()
        # options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)

    def teardown_method(self, method=None):
        self.driver.quit()

    def login(self, username="maya", password="mayah"):
        self.driver.get("http://localhost:5050/")
        self.driver.maximize_window()
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(password)
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Login')]"))).click()

    def open_cohort_builder(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.COHORT_BUILDER_LINK)).click()

    # Methods for interaction
    def click_reset(self):
        self.driver.find_element(By.CSS_SELECTOR, ".btn-danger").click()

    def click_ok_button(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']"))).click()

    def get_page_title(self):
        return self.driver.title

    def set_text_input(self, locator, value):
        element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(locator))
        element.clear()
        element.send_keys(str(value))

    def set_slider(self, slider_locator, handle_locator, value, max_value):
        track = self.driver.find_element(*slider_locator)
        handle = self.driver.find_element(*handle_locator)

        ActionChains(self.driver).click_and_hold(handle).perform()
        move_offset = int((value / max_value) * track.size["width"])
        ActionChains(self.driver).move_by_offset(move_offset - handle.location["x"], 0).release().perform()

    def check_checkbox(self, checkbox_locator):
        checkbox = self.driver.find_element(*checkbox_locator)
        if not checkbox.is_selected():
            checkbox.click()

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
        try:
            condition_def = self.conditions[condition]
            self.cohort_editor_elements[condition_def].click()
            # Wait for the dropdown options to appear and click the specified one
            option = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.XPATH, f"//div[contains(@class, 'dropdown---menu-item---1LjoL') and text()='{criteria}']")
                )
            )
            option.click()
        except Exception as e:
            print(f"Error selecting criteria: {e}")
            self.driver.save_screenshot("error.png")  # Save a screenshot to the current directory

    def select_from_multivalue_dropdown(self, labels, value=None, time_range=None, negate=False, internal_group=True):
        """
        Selects a value from a dropdown that supports multiple values being visible at once.
        #TODO internal_group
        """
        # Click to open dropdown
        dropdown = self.driver.find_element(*self.DROPDOWN_LOCATOR)
        dropdown.click()

        for label in labels:
            self.select_checkbox_by_label(label)
        # Click to close dropdown
        dropdown.click()
        if value:
            self.set_value_option_and_number(value[0], value[1])

        if time_range:
            self.set_time_range(time_range[0], time_range[1])

        if negate:
            self.check_checkbox(*self.NEGATE_LOCATOR)

        self.click_ok_button()

    def set_value_option_and_number(self, operator, value):
        """
        Sets the operator and value fields for lab tests.
        :param operator: Operator for comparison (e.g., '>', '>=', '=', '<=', '<', '!=')
        :param value: Numeric value to set for the lab test
        """
        try:
            # Locate the dropdown for selecting the operator
            operator_dropdown = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, "labs")))
            Select(operator_dropdown).select_by_value(operator)  # Select the operator by its value

            # Locate the input for entering the numeric value
            value_input = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.NAME, "labValue")))
            value_input.clear()
            value_input.send_keys(str(value))  # Convert the value to string to ensure it is accepted

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def select_checkbox_by_label(self, label_text):
        """
        Selects a checkbox within a dropdown by matching the label text.
        :param label_text: The visible text on the dropdown item to interact with, e.g., '011* PULMONARY TUBERCULOSIS (56,866)'
        """
        try:
            # Wait for the search input to be visible and enter the search text
            search_input = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".tag-list .search"))
            )
            search_input.send_keys(label_text)

            checkbox_xpath = f"//span[contains(@class,'node-label') and contains(text(),'{label_text}')]/preceding-sibling::input[@type='checkbox']"
            checkbox = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, checkbox_xpath)))
            checkbox.click()

            print(f"Checkbox for '{label_text}' clicked successfully.")

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def set_time_range(self, start_time, end_time):
        self.set_text_input(self.START_TIME_LOCATOR, start_time)
        self.set_text_input(self.END_TIME_LOCATOR, end_time)

    def set_time_scope(self, from_date, to_date):
        self.set_text_input(self.TIME_SCOPE_FROM_INPUT, from_date)
        self.set_text_input(self.TIME_SCOPE_TO_INPUT, to_date)

    def set_age_range(self, min_age, max_age):
        self.set_text_input((By.ID, "sage"), min_age)
        self.set_text_input((By.ID, "eage"), max_age)

    def start_with_login(self):
        self.login()
        print(self.driver.current_url)
        self.open_cohort_builder()
        print(self.driver.current_url)
        self.identify_cohort_cards()


t = Test()
t.start_with_login()
t.select_criteria("inclusion", "ICD9")
t.select_from_multivalue_dropdown(
    [
        "004* SHIGELLOSIS (5,164)",
    ]
)
t.select_criteria("required", "Age")
t.set_age_range(10, 50)
time.sleep(5)
t.teardown_method()
