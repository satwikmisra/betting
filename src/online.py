from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import pandas as pd
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Create chrome driver and set random location
driver = uc.Chrome()
driver.execute_cdp_cmd(
    "Browser.grantPermissions",
    {
        "origin": "https://app.prizepicks.com/",
        "permissions": ["geolocation"],
    },
)
driver.execute_cdp_cmd(
    "Emulation.setGeolocationOverride",
    {
        "latitude": 48.87645,
        "longitude": 2.26340,
        "accuracy": 100,
    },
)

# Open prizepicks
driver.get("https://app.prizepicks.com/")
time.sleep(3)

# Wait for projections to load
WebDriverWait(driver, 30).until(
    EC.presence_of_all_elements_located((By.CLASS_NAME, "close")))
time.sleep(5)

# Close the get started popup
driver.find_element(
    By.XPATH, "/html/body/div[3]/div[3]/div/div/div[3]/button").click()
time.sleep(3)

# Find the NBA button and click it
driver.find_element(
    By.XPATH, "//div[@class='name'][normalize-space()='NBA']").click()
time.sleep(5)

# Waits until stat container element is viewable
stat_container = WebDriverWait(driver, 1).until(
    EC.visibility_of_element_located((By.CLASS_NAME, "stat-container")))
categories = driver.find_element(
    By.CSS_SELECTOR, ".stat-container").text.split('\n')

data = []
for category in categories:
    driver.find_element(By.XPATH, f"//div[text()='{category}']").click()
    projections = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".projection")))

    for p in projections:
        name = p.find_element(By.CLASS_NAME, "name").text
        team_pos = p.find_element(
            By.CLASS_NAME, "team-position").text
        opponent = p.find_element(
            By.CLASS_NAME, "opponent").text.split("vs ")[1]
        value = p.find_element(
            By.CLASS_NAME, "presale-score").get_attribute('innerHTML')
        proptype = p.find_element(
            By.CLASS_NAME, "text").get_attribute('innerHTML')
        data.append({
            'name': name,
            'team': team_pos.split(" - ")[0],
            'position': team_pos.split(" - ")[1],
            'opponent': opponent,
            'stat': proptype.replace("<wbr>", ""),
            'line': value,
        })

df = pd.DataFrame(data)
df.to_csv('output.csv')
print(df)
