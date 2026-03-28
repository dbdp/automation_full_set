import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://experiences.myrealtrip.com/products/3412145")
time.sleep(3)

# Scroll in increments to trigger lazy-loaded sections
last_height = driver.execute_script("return document.body.scrollHeight")
for _ in range(10):
    driver.execute_script("window.scrollBy(0, 800);")
    time.sleep(1)

html = driver.page_source
with open("marit_test_page_scrolled.html", "w", encoding="utf-8") as f:
    f.write(html)
driver.quit()
print("Saved marit_test_page_scrolled.html")
