import os
import jsonlines
import time
import random
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from urllib.parse import urljoin

# Loading environment variables
load_dotenv()

# Configuring logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Defining constants
QUOTE_CLASS = 'quote'
NEXT_BUTTON_CLASS = 'next'

class Quote:
    def __init__(self, text, author, tags):
        self.text = text
        self.author = author
        self.tags = tags

    @classmethod
    def from_soup(cls, quote_soup):
        # Class method to create a Quote instance from a BeautifulSoup object
        try:
            text = quote_soup.find('span', class_='text').text
            author = quote_soup.find('small', class_='author').text
            tags = [tag.text for tag in quote_soup.find_all('a', class_='tag')]
            return cls(text, author, tags)
        except AttributeError:
            logging.error("Error parsing quote")
            return None

class QuoteScraper:
    # A class to scrape quotes from a website
    def __init__(self, url, output_file_name):
        self.url = url
        self.output_file_name = output_file_name
        self.driver = self.setup_driver()
        self.wait = WebDriverWait(self.driver, 15)

    def setup_driver(self):
        # Setting up the selenium driver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Defining user agents
        user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582',
        ]
        user_agent = random.choice(user_agents)
        chrome_options.add_argument(f'user-agent={user_agent}')

        # If a proxy is defined in the environment variables, use it
        proxy = os.getenv('PROXY')
        if proxy:
            webdriver.DesiredCapabilities.CHROME['proxy'] = {
                "httpProxy": proxy,
                "ftpProxy": proxy,
                "sslProxy": proxy,
                "proxyType": "MANUAL",
            }

        # Installing the chrome driver
        webdriver_service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)
        return driver

    def load_page(self, url):
        # Loading a web page with selenium and waiting until a quote appears
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, QUOTE_CLASS)))
        return BeautifulSoup(self.driver.page_source, 'lxml')

    def get_page_quotes(self, url):
        # Getting all quotes from a page
        soup = self.load_page(url)
        quotes_on_page = soup.find_all('div', class_=QUOTE_CLASS)
        return [quote for quote in (Quote.from_soup(quote_soup) for quote_soup in quotes_on_page) if quote]

    def get_next_page_url(self, url):
        # Getting the URL of the next page
        soup = self.load_page(url)
        next_button = soup.find('li', class_=NEXT_BUTTON_CLASS)
        return urljoin(url, next_button.find('a')['href']) if next_button else None

    def scrape_quotes(self, url):
        # Scraping all quotes from a page
        quotes = []
        try:
            quotes += self.get_page_quotes(url)
        except TimeoutException:
            logging.error(f"Timeout while waiting for page {url} to load.")
        return quotes

    def scrape_all_pages(self):
        # Scraping all quotes from all pages
        all_quotes = []
        while self.url is not None:
            all_quotes += self.scrape_quotes(self.url)
            self.url = self.get_next_page_url(self.url)
            if self.url:
                time.sleep(random.randint(2, 10))
        return all_quotes

    def write_quotes(self, quotes):
        # Writing the scraped quotes to a jsonlines file
        with jsonlines.open(self.output_file_name, mode='w') as writer:
            for quote in quotes:
                writer.write(quote.__dict__)

    def close_driver(self):
        # Closing the selenium driver
        self.driver.quit()


if __name__ == '__main__':
    url = os.getenv('INPUT_URL')
    output_file_name = os.getenv('OUTPUT_FILE')

    # Creating a QuoteScraper instance and scraping the quotes
    scraper = QuoteScraper(url, output_file_name)
    try:
        quotes = scraper.scrape_all_pages()
        scraper.write_quotes(quotes)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
    finally:
        scraper.close_driver()