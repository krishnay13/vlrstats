from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def get_match_ids(event_link):
    driver = webdriver.Chrome()
    # Modify the event link to point directly to the matches page
    matches_page_link = event_link.replace('/event/', '/event/matches/')
    driver.get(matches_page_link)

    # Extract the event ID from the original event link
    event_id = re.search(r'/event/(\d+)', event_link)
    if event_id:
        event_id = event_id.group(1)
    else:
        print("Could not extract event ID from the link")
        driver.quit()
        return []

    match_counter = 0
    try:
        # Wait for the matches to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href]')))
        print("Page loaded")

        # Find all anchor elements with href attributes
        match_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href]')
        print(f"Found {len(match_elements)} href elements")

        # Filter elements to get only match links
        match_ids = []
        for match_element in match_elements:
            href = match_element.get_attribute('href')
            match_id = re.search(r'/(\d+)', href)
            if match_id:
                match_id = match_id.group(1)
                # Ensure the match_id is not the same as the event ID
                if match_id != event_id:
                    match_ids.append(match_id)
                    match_counter += 1
                    print(f"Found match ID: {match_id}")

    except Exception as e:
        print(f"An error occurred: {e}")
        match_ids = []

    finally:
        driver.quit()

    print(f"Total matches found: {match_counter}")
    return match_ids


if __name__ == "__main__":
    # Test with a known event link
    test_event_link = 'https://www.vlr.gg/event/2006/champions-tour-2024-china-stage-1'
    match_ids = get_match_ids(test_event_link)
    print(f"Extracted Match IDs: {match_ids}")
