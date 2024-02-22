from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument('--headless')  # Run Chrome in headless mode (no GUI).
options.add_argument('--no-sandbox')  # Bypass OS security model; necessary in Docker.
options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems.

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.python.org")
print(driver.title)  # Print the title of the webpage.
driver.quit()
