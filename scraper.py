from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
from datetime import datetime
import time
import os

def setup_driver(chrome_userData_dir_path, profile_number):
    """
    Initialize the Selenium WebDriver with a specific Chrome profile
    """

    chromedriver_autoinstaller.install()
    
    options = webdriver.ChromeOptions()
    options.add_argument(f'--user-data-dir={chrome_userData_dir_path}')
    options.add_argument(f'--profile-directory=Profile {profile_number}')

    # options.add_argument('--headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver


def navigate_to_section(driver, url, section):
    """
    Navigate to the given Post URL and open the specified section (reblogs or likes)
    """

    driver.get(url)
    print("[INFO] Navigating to the provided Post URL...")
    time.sleep(5)

    # scroll down slightly to make the buttons visible
    driver.execute_script("window.scrollBy(0, 660);")
    print("[INFO] Scrolled the page to make buttons visible.")
    time.sleep(2)

    if section == "reblogs":
        # wait for and click the Reblogs button
        reblogs_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='Reblogs']"))
        )
        reblogs_button.click()
        print("[INFO] Reblogs button clicked.")

        # apply the "Other reblogs" filter
        filter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Other reblogs']"))
        )
        filter_button.click()
        print("[INFO] Other Blogs Filter Applied.")

    elif section == "likes":
        # wait for and click the Likes button
        likes_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='Likes']"))
        )
        likes_button.click()
        print("[INFO] Likes button clicked.")    


def save_username_pairs_to_file(batch_notes, filename):
    """
    Save a batch of username pairs to a text file.

    Args:
        batch_notes: List of Selenium WebElement notes.
        filename: Filename to save the pairs.
    """
    with open(filename, "a", encoding="utf-8") as file:
        for note in batch_notes:
            try:
                links = note.find_elements(By.CSS_SELECTOR, "a.BSUG4")
                if len(links) >= 2:
                    first_user = links[0].text.strip()
                    second_user = links[1].text.strip()
                    file.write(f"{first_user} <--> {second_user}\n")
            except Exception as e:
                print(f"[ERROR] Failed to save a username pair: {e}")
                continue
    print(f"[INFO] Saved batch of username pairs to {filename}")


def save_usernames_to_file(batch_notes, filename):
    """
    Save a batch of usernames to a text file.

    Args:
        batch_notes: List of Selenium WebElement notes.
        filename: Filename to save the usernames.
    """
    with open(filename, "a", encoding="utf-8") as file:
        for note in batch_notes:
            try:
                like_button = note.find_element(By.XPATH, ".//a[contains(@href, 'tumblr.com/') and @title]")
                username = like_button.get_attribute('title').strip()
                file.write(f"{username}\n")
            except Exception as e:
                print(f"[ERROR] Failed to save a username: {e}")
                continue
    print(f"[INFO] Saved batch of usernames to {filename}")


def scroll_and_extract(driver, section, batch_size=500, max_attempts=10):
    """
    Scroll through the notes section, extract usernames in batches, and remove processed divs.

    Args:
        driver: The Selenium WebDriver instance.
        section: The section to scrape ('reblogs' or 'likes').
        batch_size: Number of usernames to process per batch.
        max_attempts: Maximum number of attempts to scroll without new content.
    
    Returns:
        List of all extracted usernames or username pairs.
    """
    extracted_data = []  # To store all usernames or username pairs
    notes_root_div = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='notes-root']"))
    )
    print("[INFO] Found the notes root div. Starting optimized scrolling...")

    last_height = driver.execute_script("return arguments[0].scrollHeight", notes_root_div)
    rem_attempts = max_attempts
    batch_notes = []

    while True:
        # Scroll to the bottom of the notes div
        driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", notes_root_div)
        time.sleep(1)  # Wait for new notes to load

        # Extract current notes
        note_blocks = notes_root_div.find_elements(By.CSS_SELECTOR, "div[data-testid='reblog-note-block']")
        new_total_notes = len(note_blocks)

        print(f"[INFO] Total notes loaded: {new_total_notes}")

        # Calculate how many new notes have been loaded since last extraction
        if new_total_notes > len(batch_notes):
            new_notes = note_blocks[len(batch_notes):]
            for note in new_notes:
                try:
                    if section == "reblogs":
                        # Extract username pairs
                        links = note.find_elements(By.CSS_SELECTOR, "a.BSUG4")
                        if len(links) >= 2:
                            first_user = links[0].text.strip()
                            second_user = links[1].text.strip()
                            extracted_data.append((first_user, second_user))
                            batch_notes.append(note)
                    elif section == "likes":
                        # Extract single usernames
                        like_button = note.find_element(By.XPATH, ".//a[contains(@href, 'tumblr.com/') and @title]")
                        username = like_button.get_attribute('title').strip()
                        extracted_data.append(username)
                        batch_notes.append(note)
                except Exception as e:
                    print(f"[ERROR] Failed to extract data from a note: {e}")
                    continue

            print(f"[INFO] Extracted {len(new_notes)} new notes.")

            # Check if batch_size is reached
            if len(batch_notes) >= batch_size:
                # Save the current batch
                if section == "reblogs":
                    save_username_pairs_to_file(batch_notes, filename=f"username_pairs_batch_{len(extracted_data)}.txt")
                elif section == "likes":
                    save_usernames_to_file(batch_notes, filename=f"likes_usernames_batch_{len(extracted_data)}.txt")
                
                # Remove the processed divs from the DOM
                for note in batch_notes:
                    driver.execute_script("""
                        var element = arguments[0];
                        element.parentNode.removeChild(element);
                    """, note)
                print(f"[INFO] Removed {len(batch_notes)} processed notes from the DOM.")
                
                # Reset batch_notes for the next batch
                batch_notes = []

            rem_attempts = max_attempts  # Reset remaining attempts since new content was loaded
        else:
            rem_attempts -= 1
            print(f"[INFO] No new notes loaded. Remaining attempts: {rem_attempts}")
            if rem_attempts == 0:
                print("[INFO] Scrolling completed. No more new content to load.")
                break

        # Optionally, check if the scroll height has not changed to decide when to stop
        new_height = driver.execute_script("return arguments[0].scrollHeight", notes_root_div)
        if new_height == last_height:
            rem_attempts -= 1
            if rem_attempts == 0:
                print("[INFO] Reached the end of the notes section.")
                break
        else:
            last_height = new_height

    return extracted_data


def main():
    """
    Main function to execute the script
    """

    # Get the Chrome user data directory path and the profile number where `Tumblr` account is logged in.
    chrome_userdata_dir_path = input("Enter the path to your Chrome User Data Directory: ").replace('\\', '/')
    chrome_profile_number = int(input("Enter the Chrome Profile number: "))

    # Get the post URL from the user
    post_url = input("Enter the URL of the Tumblr Post: ")

    # Input the section (likes/reblogs) which user wanna scrape
    section = input("Enter the section to scrape (reblogs/likes): ").strip().lower()
    if section not in ["reblogs", "likes"]:
        print("[ERROR] Invalid section. Please choose either 'reblogs' or 'likes'.")
        return

    # Set up the webdriver
    driver = setup_driver(chrome_userdata_dir_path, chrome_profile_number)

    try:
        navigate_to_section(driver, post_url, section)
        extracted_data = scroll_and_extract(driver, section)

        # Final confirmation
        print(f"[INFO] Extraction completed. Total items extracted: {len(extracted_data)}")

    finally:
        driver.quit()
        print("[INFO] WebDriver closed.")


if __name__ == "__main__":
    main()
