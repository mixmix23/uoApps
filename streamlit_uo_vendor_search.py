import streamlit as st
import time
import os
import threading
from dotenv import load_dotenv
import pygame
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

DEFAULT_EMAIL = os.getenv("UO_EMAIL")
DEFAULT_PASSWORD = os.getenv("UO_PASSWORD")

# --- Session state flags ---
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_paused' not in st.session_state:
    st.session_state.bot_paused = False

stop_flag = threading.Event()
pause_flag = threading.Event()

def play_alert_sound():
    pygame.mixer.init()
    pygame.mixer.music.load("chime-alert-demo-309545.mp3")
    pygame.mixer.music.play()

def perform_search(driver, wait, search_term, max_price):
    driver.get("https://portal.uooutlands.com/vendor-search")
    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search']"))
    )
    search_input.clear()
    search_input.send_keys(search_term)
    search_input.send_keys(Keys.RETURN)
    time.sleep(1)

    rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.cdk-row")))
    print(f"\nChecking for matches at {time.strftime('%X')} for '{search_term}'...")

    matches_found = False
    lowest_price = None
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

            if search_term.lower() in name:
                if price < max_price:
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

                    link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                    print(f"Opening listing: {link}")
                    driver.execute_script("window.open(arguments[0], '_blank');", link)
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.switch_to.window(main_window)
                    matches_found = True

        except Exception as e:
            print("Error parsing row:", e)

    if matches_found:
        play_alert_sound()
    else:
        if lowest_price:
            print(f"No matches under {max_price:,} for '{search_term}' — lowest was {lowest_price:,}")
        else:
            print(f"No results found for '{search_term}'")

def threaded_bot(username, password, term_price_list, interval):
    stop_flag.clear()
    pause_flag.clear()
    st.session_state.bot_running = True
    st.session_state.bot_paused = False

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    driver.get("https://portal.uooutlands.com/login")
    driver.find_element(By.NAME, "outlandsId").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/home"))
    print("Login successful.")

    try:
        while not stop_flag.is_set():
            if pause_flag.is_set():
                print("Bot paused. Waiting...")
                time.sleep(1)
                continue

            for term, price in term_price_list:
                perform_search(driver, wait, term.strip(), price)
                if stop_flag.is_set() or pause_flag.is_set():
                    break

            # Wait interval if not paused or stopped
            for _ in range(interval):
                if stop_flag.is_set() or pause_flag.is_set():
                    break
                time.sleep(1)

    except Exception as e:
        print("Bot error:", e)
    finally:
        st.session_state.bot_running = False
        st.session_state.bot_paused = False
        print("Bot stopped.")

# --- Streamlit UI ---
st.title("UO Outlands Vendor Search Bot")

with st.form("bot_form"):
    username = st.text_input("UOOutlands Email", value=DEFAULT_EMAIL)
    password = st.text_input("Password", type="password", value=DEFAULT_PASSWORD)

    st.markdown("### Enter one search term and its max price per line")
    st.caption("Format: search term, max price")
    raw_input = st.text_area("Search Terms + Max Price (one per line)")

    interval = st.slider("Search Interval (seconds)", min_value=30, max_value=600, value=120, step=30)
    submitted = st.form_submit_button("Start Bot")

if submitted:
    entries = []
    errors = []

    for line in raw_input.strip().splitlines():
        parts = [p.strip() for p in line.rsplit(",", 1)]
        if len(parts) != 2:
            errors.append(f"❌ Invalid format: '{line}'")
            continue
        term, price_str = parts
        try:
            price = int(price_str.replace(",", ""))
            entries.append((term, price))
        except ValueError:
            errors.append(f"❌ Invalid price in: '{line}'")

    if not username or not password:
        st.warning("Username and password are required.")
    elif errors:
        for err in errors:
            st.error(err)
    elif not entries:
        st.warning("Please enter at least one valid search term and price.")
    elif st.session_state.bot_running:
        st.warning("Bot is already running.")
    else:
        st.success("✅ Bot is starting... check your terminal.")
        threading.Thread(target=threaded_bot, args=(username, password, entries, interval), daemon=True).start()

# Pause / Resume / Stop Buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.bot_running and not st.session_state.bot_paused:
        if st.button("⏸ Pause Bot"):
            pause_flag.set()
            st.session_state.bot_paused = True
            st.success("Bot paused.")
    elif st.session_state.bot_paused:
        st.info("Bot is paused.")

with col2:
    if st.session_state.bot_running and st.session_state.bot_paused:
        if st.button("▶️ Resume Bot"):
            pause_flag.clear()
            st.session_state.bot_paused = False
            st.success("Bot resumed.")

with col3:
    if st.session_state.bot_running:
        if st.button("🛑 Stop Bot"):
            stop_flag.set()
            st.session_state.bot_paused = False
            st.success("Bot stopping...")

if not st.session_state.bot_running and not st.session_state.bot_paused:
    st.info("Bot is not running.")
