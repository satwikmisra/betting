from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import pandas as pd
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


def scrape_prizepicks(sport):
    # set random location or else prizepicks catches on lol
    driver = uc.Chrome(version_main=120)
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
    driver.get("https://app.prizepicks.com/")
    time.sleep(3)

    # wait for projections to load
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "close")))
    time.sleep(2)

    # need to close the get started popup before interacting with other shit
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div[3]/div/div/div[3]/button").click()
    time.sleep(2)

    # choose sport (needs to be available on the board at the time of running or else will error)
    driver.find_element(
        By.XPATH, f"//div[@class='name'][normalize-space()='{sport}']").click()
    time.sleep(5)

    WebDriverWait(driver, 1).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "stat-container")))
    categories = driver.find_element(
        By.CSS_SELECTOR, ".stat-container").text.split('\n')
    data = []
    for category in categories:
        # for each stat scrape cards/projections
        driver.find_element(By.XPATH, f"//div[text()='{category}']").click()
        projections = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".projection")))

        for pi, p in enumerate(projections):
            name = p.find_element(By.CLASS_NAME, "name").text
            team_pos = p.find_element(
                By.CLASS_NAME, "team-position").text
            opponent = p.find_element(
                By.CLASS_NAME, "opponent").text.split("vs ")[1]
            value = p.find_element(
                By.CLASS_NAME, "presale-score").get_attribute('innerHTML')
            proptype = p.find_element(
                By.CLASS_NAME, "text").get_attribute('innerHTML')
            date = p.find_element(
                By.CLASS_NAME, "date").get_attribute('innerText')

            # handles games starting in < 1 hour, ask neer if this is implemented correctly
            if 'Start' in date:
                date = datetime.now()
            else:
                date = datetime.strptime(
                    date + f" {datetime.now().year}", "%a, %b %d %I:%M %p %Y")
            date = date.strftime("%m/%d/%Y %H:%M:%S")
            game_date = date.split(" ")[0]
            game_time = date.split(" ")[1]
            game_date = datetime.strptime(game_date, "%m/%d/%Y")
            game_date = game_date.strftime("%Y-%m-%d")
            data.append({
                'name': name,
                'team': team_pos.split(" - ")[0],
                'position': team_pos.split(" - ")[1],
                'opponent': opponent,
                'stat': proptype.replace("<wbr>", ""),
                'line': value,
                'date': game_date,
                'time': game_time,
            })
            print(f'{sport} | {category} ==> scraped {pi+1}/{len(projections)}')
    driver.quit()
    return pd.DataFrame(data)


def save_lines_csv(sport):
    timestamp = datetime.now().isoformat()
    df = scrape_prizepicks(sport)
    filename = f'{sport}_prizepicks_{timestamp}.csv'
    df.to_csv(filename, index=False)
    print(f'Saved lines to {filename}')


if __name__ == '__main__':
    save_lines_csv('LoL')
    save_lines_csv('CS2')
