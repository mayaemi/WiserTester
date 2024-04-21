import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class TestCohortBuilder:
    def __init__(self):
        self.driver = None

        # definitions

        self.expected_elements = {
            "General": ["svg"],
            "Survival": ["img"],
            "Relative Risk": ["table"],
            "Cohort Predisposition": ["table"],
            "Labs": ["img"],
            "Trends": ["img"],
            "Age Trends": ["img"],
            "Medications": ["img"],
            "Clustering": ["img", "svg"],
        }
        self.conditions = {
            "inclusion": "cohortBuild_cohort_inclusionCriteria",
            "required": "cohortBuild_cohort_requiredFilter",
            "exclusion": "cohortBuild_cohort_excludeFilter",
            "onset": "cohortBuild_cohort_adjustOnsetTime",
        }
        # Locators
        self.COHORT_BUILDER_LINK = (By.XPATH, "//a[contains(text(),'Cohort Builder')]")
        self.NAVBAR_BRAND = (By.CSS_SELECTOR, "a.navbar-brand")
        self.STATUS_BUBBLE = (By.CSS_SELECTOR, "div.status-bubble.mb-2.card")
        self.GRAPH_ELEMENTS = (By.CSS_SELECTOR, "div.react-grid-item.cssTransforms")

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

    @staticmethod
    def get_chrome_options():
        options = Options()
        # options.headless = True  # Running in headless mode
        options.add_argument("window-size=1200x600")  # Define window size to avoid element being off-screen

        # Enable logging
        caps = DesiredCapabilities.CHROME
        caps["loggingPrefs"] = {"browser": "ALL"}  # Capture all browser logs including console outputs
        options.add_argument("--enable-logging")
        options.add_argument("--v=1")
        return options

    def setup_method(self, method=None):
        self.driver = webdriver.Chrome(options=self.get_chrome_options())
        self.driver.implicitly_wait(10)

    def teardown_method(self, method=None):
        self.driver.quit()

    def print_browser_logs(self, context=""):
        # Retrieve browser logs
        for entry in self.driver.get_log("browser"):
            if entry["level"] == "ERROR":
                logging.error(f"{context} - {entry['message']}")
            else:
                logging.debug(f"{context} - {entry['message']}")

    def login(self, username="maya", password="mayah"):
        try:
            self.driver.get("http://localhost:5050/")
            self.driver.maximize_window()
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(password)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Login')]"))).click()
            logging.info("Logged in successfully")
        except Exception as e:
            logging.error(f"Failed to log in: {e}")
            self.driver.save_screenshot("login_error.png")

    def open_cohort_builder(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.COHORT_BUILDER_LINK)).click()
            logging.info("Cohort Builder opened")
        except TimeoutException:
            logging.error("Cohort Builder link not clickable")
            self.driver.save_screenshot("cohort_builder_error.png")

    def verify_cohort_creation(self):
        # Verify the status bubble with 'n patients'
        try:
            status_bubble = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.STATUS_BUBBLE))
            patient_count_text = status_bubble.text
            if "patients" in patient_count_text:
                logging.info(f"Cohort creation verified with text: {patient_count_text}")
            else:
                logging.warning(f"Status bubble text might not indicate success: {patient_count_text}")

        except TimeoutException:
            logging.error("Failed to verify cohort creation (status bubble or graphs missing).")
            self.driver.save_screenshot("cohort_verification_error.png")

    def verify_elements_on_tab(self, tab):
        tab_name = tab.text.strip()
        logging.info(f"Checking elements on tab: {tab_name}")

        if tab_name not in self.expected_elements:
            logging.warning(f"No expected elements defined for tab: {tab_name}")
            return
        # Wait for any general loading indicator to disappear
        WebDriverWait(self.driver, 30).until_not(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'loading')]"))
        )

        element_type_status = {}

        for element_type in self.expected_elements[tab_name]:
            try:
                elements = WebDriverWait(self.driver, 30).until(EC.presence_of_all_elements_located((By.TAG_NAME, element_type)))
                if not elements:
                    element_type_status[element_type] = False
                    logging.error(f"No {element_type} elements found on {tab_name} despite being expected.")
                else:
                    element_type_status[element_type] = True
                    for e in elements:
                        try:
                            card_header = e.find_element(
                                By.XPATH,
                                ".//ancestor::div[contains(@class, 'mb-0card')][.//div[@class='card-header']]//div[@class='card-header']",
                            ).text
                            logging.info(f"{element_type} {card_header} loaded")
                        except Exception:
                            pass

                    logging.info(f"All elements successfully loaded on tab {tab.text.strip()}")
            except TimeoutException:
                element_type_status[element_type] = False
                logging.error(f"Timeout waiting for {element_type} on tab {tab_name}")

        self.log_unfinished_components(tab, element_type_status)

    def verify_graphs_across_tabs(self, exclude=None):
        if exclude is None:
            exclude = ["Labs", "Trends", "Age Trends", "Medications", "Clustering"]
        tabs = WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".react-tabs__tab")))
        for tab in tabs:
            if tab.text.strip() not in exclude:
                try:
                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(tab)).click()
                    self.verify_elements_on_tab(tab)

                except ElementClickInterceptedException:
                    logging.error(f"Couldn't click tab {tab.text.strip()} due to an overlay or positioning issue.")
                except Exception as e:
                    logging.error(f"An unexpected error occurred on tab {tab.text.strip()}: {str(e)}")

    def log_unfinished_components(self, tab, elements_status):
        # Log the header of the card that contains not fully loaded elements
        for element, status in elements_status.items():
            if not status:  # If any element type was not loaded completely
                try:
                    # Find the parent card of the unfinished element(s)
                    loading_elements = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'loading')]")
                    for loading_element in loading_elements:
                        card_header = loading_element.find_element(
                            By.XPATH, "./ancestor::div[contains(@class, 'mb-0 card')]/div[@class='card-header']"
                        )
                        logging.error(
                            f"Unfinished loading '{element}' in card titled '{card_header.text}' on tab '{tab.text.strip()}'."
                        )
                except NoSuchElementException:
                    logging.error(
                        f"Failed to find the card header for the unfinished {element} elements on tab '{tab.text.strip()}'."
                    )

    # Methods for interaction
    def scroll_into_view(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def safe_click(self, element):
        try:
            self.scroll_into_view(element)
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    def click_reset(self):
        self.driver.find_element(By.CSS_SELECTOR, ".btn-danger").click()

    def click_ok_button(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='OK']"))).click()
            logging.info("OK button clicked")
        except TimeoutException:
            logging.error("OK button not clickable")
            self.driver.save_screenshot("ok_button_error.png")

    def get_page_title(self):
        return self.driver.title

    def wait_for_page_load(self, timeout=30):
        WebDriverWait(self.driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

    def wait_for_interactivity(self, element_locator, timeout=10):
        """
        Waits for an element to be clickable, indicating it's fully loaded and interactive.
        """
        try:
            WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(element_locator))
            logging.info(f"Element {element_locator} is ready for interaction.")
        except TimeoutException:
            logging.error(f"Element {element_locator} not ready for interaction after {timeout} seconds.")
            self.driver.save_screenshot("element_not_interactive.png")

    def reacquire_element_after_action(self, locator):
        """
        Re-acquires an element after performing actions that may have altered the DOM.
        Useful for dynamic content that gets reloaded or updated.
        """
        try:
            return WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            logging.error(f"Failed to re-acquire element {locator}.")
            self.driver.save_screenshot("reacquire_element_error.png")
            return None

    def set_text_input(self, locator, value):
        try:
            element = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(locator))
            element.clear()
            element.send_keys(str(value))
            logging.info(f"Set text input at {locator}: {value}")
        except Exception as e:
            logging.error(f"Failed to set text in input field {locator}: {e}")
            self.driver.save_screenshot("input_field_error.png")

    def set_slider(self, slider_locator, handle_locator, value, max_value):
        track = self.driver.find_element(*slider_locator)
        handle = self.driver.find_element(*handle_locator)

        ActionChains(self.driver).click_and_hold(handle).perform()
        move_offset = int((value / max_value) * track.size["width"])
        ActionChains(self.driver).move_by_offset(move_offset - handle.location["x"], 0).release().perform()

    def set_time_range(self, start_time, end_time):
        self.set_text_input(self.START_TIME_LOCATOR, start_time)
        self.set_text_input(self.END_TIME_LOCATOR, end_time)

    def set_time_scope(self, from_date, to_date):
        self.set_text_input(self.TIME_SCOPE_FROM_INPUT, from_date)
        self.set_text_input(self.TIME_SCOPE_TO_INPUT, to_date)

    def set_age_range(self, min_age, max_age):
        self.set_text_input((By.ID, "sage"), min_age)
        self.set_text_input((By.ID, "eage"), max_age)

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
        try:
            elements = self.driver.find_element(*self.COHORT_EDITOR)
            # elements = self.driver.find_elements(*self.COHORT_EDITOR)
            for element in elements.find_elements(By.XPATH, ".//div[@class='card-body']"):
                name = element.get_attribute("id")
                self.cohort_editor_elements[name] = element
            logging.info(f"Cohort cards identified: {self.cohort_editor_elements}")
        except Exception as e:
            logging.error("Failed to identify cohort cards")
            self.driver.save_screenshot("cohort_cards_error.png")

    def open_criteria_menu(self, condition):
        try:

            # Retrieve the specific dropdown button for the condition using its stored ID from the conditions dictionary
            element = self.cohort_editor_elements[self.conditions[condition]]
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, self.conditions[condition])))

            drop_button = element.find_element(By.XPATH, "..").find_element(By.XPATH, ".//button[@type='button']")
            drop_button.click()
            logging.info(f"Dropdown menu for condition '{condition}' opened successfully.")

        except Exception as e:
            logging.error(f"An error occurred while trying to open the dropdown for condition '{condition}': {e}")
            self.driver.save_screenshot(f"{condition}_dropdown_error.png")

    def select_criteria(self, condition, criteria):
        try:
            self.open_criteria_menu(condition)
            # Wait a moment for the dropdown to fully expand and for its contents to be interactive
            time.sleep(1)
            # Select the criteria from the dropdown
            criteria_locator = (
                By.XPATH,
                f".//div[contains(@class, 'dropdown---menu-item---1LjoL') and normalize-space()='{criteria}']",
            )
            self.wait_for_interactivity(criteria_locator)
            criteria_option = self.driver.find_element(*criteria_locator)
            criteria_option.click()
            logging.info(f"Criteria '{criteria}' selected under condition '{condition}'")

        except Exception as e:
            logging.error(f"Error selecting criteria '{criteria}' under condition '{condition}': {e}")
            self.driver.save_screenshot("select_criteria_error.png")

    def select_from_multivalue_dropdown(self, labels, value=None, time_range=None, negate=False, internal_group=True):
        """
        Selects a value from a dropdown that supports multiple values being visible at once.
        #TODO internal_group
        """
        try:
            dropdown = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located(self.DROPDOWN_LOCATOR))
            dropdown.click()
            for label in labels:
                self.select_checkbox_by_label(label)
            if value:
                self.set_value_option_and_number(value[0], value[1])
            if time_range:
                self.set_time_range(time_range[0], time_range[1])
            if negate:
                self.check_checkbox(self.NEGATE_LOCATOR)
            dropdown.click()  # To close the dropdown
            self.click_ok_button()
            logging.info("Multi-value dropdown selections applied")
        except Exception as e:
            logging.error(f"Error handling multi-value dropdown: {e}")
            self.driver.save_screenshot("multi_value_dropdown_error.png")

    def set_value_option_and_number(self, operator, value):
        """
        Sets the operator and value fields for lab tests.
        :param operator: Operator for comparison (e.g., '>', '>=', '=', '<=', '<', '!=')
        :param value: Numeric value to set for the lab test
        """
        try:
            operator_dropdown = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.ID, "labs")))
            Select(operator_dropdown).select_by_value(operator)

            value_input = WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.NAME, "labValue")))
            value_input.clear()
            value_input.send_keys(str(value))

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def select_checkbox_by_label(self, label_text):
        """
        Selects a checkbox within a dropdown by matching the label text.
        :param label_text: The visible text on the dropdown item to interact with, e.g., '011* PULMONARY TUBERCULOSIS (56,866)'
        """
        try:
            checkbox_xpath = f"//span[contains(@class,'node-label') and contains(text(),'{label_text}')]/preceding-sibling::input[@type='checkbox']"
            checkbox = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, checkbox_xpath)))
            checkbox.click()
            logging.info(f"Checkbox for '{label_text}' clicked")
        except Exception as e:
            logging.error(f"Failed to click checkbox for '{label_text}': {e}")
            self.driver.save_screenshot("checkbox_error.png")

    def initialize_cohort_builder(self):
        self.login()
        self.open_cohort_builder()
        self.identify_cohort_cards()


t = TestCohortBuilder()  #
t.initialize_cohort_builder()
t.select_criteria("inclusion", "ICD9")
t.select_from_multivalue_dropdown(["004* SHIGELLOSIS (5,164)"])
time.sleep(2)
t.verify_cohort_creation()
t.verify_graphs_across_tabs()
t.print_browser_logs()
# t.select_criteria("required", "ICD9")
# t.select_from_multivalue_dropdown(["101 WBC"], time_range=[-180, 180])
t.teardown_method()
