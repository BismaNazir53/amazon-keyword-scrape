#To run this script you should have a google sheet with name item keywords and item urls.
#The access of above 2 files should be shared with the email in cred file.
#this code will pick up the keyword from one file and scrape the products urls for that keyword
#and store the keyword and 10 urls in item url sheet.

#Libraries for selenium environment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

#To connect with google docs
import googleapiclient.discovery
import gspread
import pygsheets
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import webbrowser

# To detect language
import re
from datetime import date
import time
from datetime import datetime

global client, credentials, scope, scraped_links, item_url
run_local=True
#This function gets a keyword as input and open the amazon url using selenium
#and search 10 keywords and get urls of the products with price greater than 25$
#and rating greater than 4.2 stars and reviews greater than 100.
def get_url(keyword):
    #Setting up browser for local run
    if(run_local):
        # Set up browser for scraping
        chrome_options = Options()
        # chrome_options.add_argument('--headless')
        chrome_service = Service('chromedriver')
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    #----------------------------------------------------------------------------- 
    #setup heroku
    if(not(run_local)):
         
        global user_agents
        user_agents = []
        with open('user_agents.csv', 'r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                user_agents.append(row[0])

        # Select a random user agent
        user_agent = random.choice(user_agents)
        print("User Agent", user_agent)
        
        #Setting up driver for server run on server
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--user-agent={user_agent}')        
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
    
    amazon_url='https://www.amazon.com/'
    driver.get(amazon_url)
    
    try:
        #Enter keyword in searchbar
        searchbox_xpath='//*[@id="twotabsearchtextbox"]'
        wait = WebDriverWait(driver, 20)
        searchbox = wait.until(EC.presence_of_element_located((By.XPATH, searchbox_xpath)))
        searchbox_search=searchbox.send_keys(keyword)
        searbutton_xpath ='//*[@id="nav-search-submit-button"]'
        searchbutton=driver.find_element(By.XPATH,searbutton_xpath)
        searchbutton.click()
    except Exception as e:
        print("No searchbox",e)
        driver.quit()
        return
        
    observed_products=0
    # Variable to See 25 products
    total_products=25
    temp_dict={}
    while(observed_products<total_products):
        try:
            print('url', driver.current_url)
            box_xpath = "//div[@data-component-type='s-search-result']/div[contains(@class, 'sg-col-inner')]/div"
            box_elements = driver.find_elements(By.XPATH, box_xpath)
            total_boxes = len(box_elements)
            print("Total Boxes", total_boxes)
            i=0
            for features in box_elements:
                i=i+1
                if(observed_products<=total_products):
                    print("Observed products, total", observed_products, total_products)
                    try:
                        #Get number of reviews
                        reviews_number_xpath = './/span[@class="a-size-base s-underline-text"]'
                        review_element = features.find_element(By.XPATH, reviews_number_xpath)
                        review = review_element.text
                        print("Number of reviews", review)
                        review = (review.replace(',', ''))
                        #if number of reviews are greater than 100 get its price
                        if(int(review)>100):
                            price_xpath = './/span[@class="a-price"]/span[1]'
                            price_element = features.find_element(By.XPATH, price_xpath)
                            price = price_element.get_attribute('textContent')
                            price = price[1:-3].strip()
                            print("price", price)
                            #If price is greater than or equal to 24 then get its rating
                            if (int(price) >= 24):
                                rating_xpath = './/span[@class="a-icon-alt"]'
                                rating_element = features.find_element(By.XPATH, rating_xpath)
                                rating = rating_element.get_attribute('textContent')
                                match = re.search(r"[0-9]+\.[0-9]", rating)
                                # Get the number
                                rating = match.group(0).strip()
                                print("rating", rating)
                                #if rating is greaten than or equal to 4.2 then get link of products
                                if (float(rating) >= 4.2):
                                    link_xpath = './/a[@class="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal"]'
                                    link_element = features.find_element(By.XPATH, link_xpath)
                                    link = link_element.get_attribute('href')
                                    print("Link", link)
                                    #add link and review number in dictionary to get the top 10
                                    temp_dict[review] = link
                                    observed_products=observed_products+1
                                    print("temp_dict", temp_dict)
                    except Exception as e:
                        print("Missing Element",e)
            try:
                #If there are less then 25 products on first page then get more products from next page.
                next_page_xpath = '//span[@class="s-pagination-strip"]/a[@class="s-pagination-item s-pagination-next s-pagination-button s-pagination-separator"]'
                next_page_element = driver.find_element(By.XPATH, next_page_xpath)
                driver.get(next_page_element.get_attribute('href'))
                time.sleep(10)
            except Exception as e:
                print("No Next Page exists",e)
                driver.quit()
                break
        except Exception as e:
            print("Please Try anyother keyword",e)
            driver.quit()
            
    today = datetime.today().strftime("%B %d, %Y")
    # Get the top 10 elements with the highest numbers in the key
    # Sort the dictionary items by keys in descending order and get the top 10 items
    sorted_items = sorted(temp_dict.items(), key=lambda x: int(x[0]), reverse=True)[:10]

    # Extract the values from the sorted items
    result = [item[1] for item in sorted_items]
    print("result:", result)
    #input("O")
    #update the google sheet with keyword and link of the products
    for link in result:
        item_url.append_row([today, str(keyword), link])

    print("Sheet updated")
    driver.quit()
    return
    
#This function connects with googlesheets and gets keywords from a googlesheet and
#calls a function get_url with the input as keyword and make a list for those keywords
#that has been used.
def get_keywords():
    global client, credentials, scope,item_url
    # Connect to Google Sheets API
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('cred.json', scope)
    client = gspread.authorize(credentials)

    # SHeet name where urls of all the items to be scraper are stores.
    spreadsheet = client.open('Item keywords')
    keywords_worksheet = spreadsheet.sheet1
    # Retrieve URLs from each row of the Google Sheet
    # Assuming URLs are in column A, starting from row 1
    keywords = keywords_worksheet.col_values(1)[0:]
    
    item_url=client.open('Item URL')
    item_url=item_url.sheet1
    print("items",item_url.url)
    
    scraped_keywords=item_url.col_values(2)[0:]
    #print(keywords)
    # Iterate through each keyword and open it using Selenium
    for keyword in keywords:
        # search and get URL
        if (keyword not in scraped_keywords): #if keyword is not already scraped.
            get_url(keyword)
    
    return
    
def main():
    get_keywords()
    print("I have completed my scrapping")


# #===============================================================================

if __name__ == "__main__":
    main()
