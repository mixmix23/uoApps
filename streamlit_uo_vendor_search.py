import streamlit as st
import time
import pygame
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def play_alert_sound():
    pygame.mixer.init()
    pygame.mixer.music.load("chime-alert-demo-309545.mp3")
    pygame.mixer.music.play()

def perform_search(driver, wait, search_term, price_limit):
    lowest_price = None
    matches_found = False

    driver.get("https://portal.uooutlands.com/vendor-search")
    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search']")))
    search_input.clear()
    search_input.send_keys(search_term)
    time.sleep(1)
    search_input.send_keys(Keys.RETURN)

    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.cdk-row")))
    main_window = driver.current_window_handle

    for row in rows:
        try:
            name_el = row.find_element(By.CLASS_NAME, "mat-column-name")
            price_el = row.find_element(By.CLASS_NAME, "mat-column-price")
            map_el = row.find_element(By.CLASS_NAME, "mat-cell-content")

            name = name_el.text.lower()
            price_text = price_el.text.replace(",", "")
            price = int("".join(filter(str.isdigit, price_text)))

            if lowest_price is None or price < lowest_price:
                lowest_price = price

            if search_term.lower() in name and price <= price_limit:
                st.success(f"[{search_term}] Match: {name} — {price:,}")
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
                    st.write(f"[Open Listing]({link})", unsafe_allow_html=True)
                    driver.execute_script("window.open(arguments[0], '_blank');", link)
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.switch_to.window(main_window)
                except Exception as e:
                    st.warning(f"Could not open listing: {e}")

                matches_found = True

        except Exception as e:
            st.warning(f"Error parsing row: {e}")

    if matches_found:
        play_alert_sound()
    else:
        st.info(f"[{search_term}] No matches under {price_limit:,} — lowest: {lowest_price:,}" if lowest_price else f"[{search_term}] No listings found")

    return matches_found

def start_bot(username, password, search_entries, interval):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")    # Prevents Chrome crash
    options.add_argument("--disable-dev-shm-usage")  # Fix for low memory

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://portal.uooutlands.com/login")
        driver.find_element(By.NAME, "outlandsId").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        wait.until(EC.url_contains("/home"))

        st.success("Login successful. Bot running...")
        st.session_state.running = True

        while st.session_state.running:
            st.write(f"🔍 Checking {len(search_entries)} terms at {time.strftime('%X')}...")
            any_matches = False
            for entry in search_entries:
                term = entry['term']
                price = entry['price']
                if perform_search(driver, wait, term, price):
                    any_matches = True
                time.sleep(1)
            if not any_matches:
                st.write(f"No matches found at {time.strftime('%X')}.")
            time.sleep(interval)

    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        st.warning("Bot stopped.")

# --- Streamlit UI ---
st.set_page_config(page_title="UO Vendor Bot", layout="centered")
st.title("UO Outlands Vendor Search Bot — Multi-Term + Price + Stop")

# Initialize session state
if "running" not in st.session_state:
    st.session_state.running = False

with st.form("search_form"):
    username = st.text_input("UOOutlands Email")
    password = st.text_input("Password", type="password")
    st.markdown("**Search Terms** (Format: `term | price` per line. Example: `blank scroll | 500`)")
    search_terms_text = st.text_area("Search Terms", value="leather commodity (5,000 held per commodity) | 13000")
    default_price = st.number_input("Default Max Price (used if no price on line)", value=13000, step=500)
    interval = st.number_input("Search Interval (seconds)", value=120, step=10)
    submitted = st.form_submit_button("Start Bot")

if submitted and username and password:
    # Parse lines into search entries with individual price limits
    search_entries = []
    for line in search_terms_text.strip().splitlines():
        parts = [part.strip() for part in line.split("|")]
        if not parts[0]:
            continue
        search_term = parts[0]
        price = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else default_price
        search_entries.append({"term": search_term, "price": price})

    if search_entries:
        start_bot(username, password, search_entries, interval)
    else:
        st.warning("No valid search terms entered.")

# Stop button
if st.session_state.running:
    if st.button("🛑 Stop Bot"):
        st.session_state.running = False
