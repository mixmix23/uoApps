import time
import pygame
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

USERNAME = "mixmix23@gmail.com"
PASSWORD = "S@ndi3123!"
SEARCH_TERM = "leather commodity (5,000 held per commodity)"
MAX_PRICE = 13000
SEARCH_INTERVAL = 120  # seconds (2 minutes)

def play_alert_sound():
    pygame.mixer.init()
    pygame.mixer.music.load("chime-alert-demo-309545.mp3")
    pygame.mixer.music.play()

def perform_search(driver, wait):
    lowest_price = None

    driver.get("https://portal.uooutlands.com/vendor-search")
    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search']"))
    )
    search_input.clear()
    search_input.send_keys(SEARCH_TERM)
    time.sleep(1)
    search_input.send_keys(Keys.RETURN)

    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.cdk-row")))

    matches_found = False
    print(f"\nChecking for matches at {time.strftime('%X')}...")

    main_window = driver.current_window_handle  # Remember main search tab

    for row in rows:
        try:
            name_el = row.find_element(By.CLASS_NAME, "mat-column-name")
            price_el = row.find_element(By.CLASS_NAME, "mat-column-price")
            map_el = row.find_element(By.CLASS_NAME, "mat-cell-content")

            name = name_el.text.lower()
            price_text = price_el.text.replace(",", "")
            price = int("".join(filter(str.isdigit, price_text)))

            # Track the lowest price even if no matches are found
            if lowest_price is None or price < lowest_price:
                lowest_price = price

            if SEARCH_TERM in name:
                if price < MAX_PRICE:
                    print(f"Match: {name} — {price:,}")

                    driver.execute_script("""
                        arguments[0].style.backgroundColor = '#39FF14';  
                        arguments[0].style.border = '2px solid black';
                        arguments[0].style.color = 'black';              
                    """, price_el)

                    driver.execute_script("""
                        arguments[0].style.backgroundColor = '#39FF14';
                        arguments[0].style.border = '2px solid black';
                        arguments[0].style.color = 'black';
                    """, map_el)

                    try:
                        link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                        print(f"Opening listing: {link}")

                        # Open link in new tab controlled by Selenium
                        driver.execute_script("window.open(arguments[0], '_blank');", link)
                        driver.switch_to.window(driver.window_handles[-1])  # Switch to new tab

                        # You can add any code here to interact with the new tab if desired
                        # For example: scrape details, take screenshot, etc.

                        # Switch back to main tab when done
                        driver.switch_to.window(main_window)

                    except Exception as e:
                        print("Could not find link in row:", e)

                    matches_found = True

        except Exception as e:
            print("Error parsing row:", e)

    if matches_found:
        print("Matches found! Playing alert sound...")
        play_alert_sound()
    else:
        print(f"No matches under {MAX_PRICE:,} for '{SEARCH_TERM}' — lowest available is {lowest_price:,}")

def main():
    options = webdriver.ChromeOptions()
    # options.add_experimental_option("detach", True)  # Optional, if you want browser to stay open after script ends
    # options.add_argument("--headless")  # Make sure this is disabled to see browser windows
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    wait = WebDriverWait(driver, 10)

    # Log in
    driver.get("https://portal.uooutlands.com/login")
    driver.find_element(By.NAME, "outlandsId").send_keys(USERNAME)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    wait.until(EC.url_contains("/home"))

    try:
        while True:
            perform_search(driver, wait)
            time.sleep(SEARCH_INTERVAL)  # wait before next check
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        print("\nWebpage left open")
        # driver.quit()  # Commented out so browser stays open

if __name__ == "__main__":
    main()
