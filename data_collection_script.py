from pdf2image import convert_from_path as cfp
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from threading import Thread

# declare global variables
path = "where the files are"
compositions = {"composer": ["list", "of", "compositions"],
                "composer2": ["make sure", "composer", "is in", "lowercase"]
                }


def to_image(composer, composition):
    '''
    Convert PDF to JPEG file(s)
    '''
    image = cfp((path+composer+"\\"+composition+".pdf"), poppler_path=r"your path\poppler-23.01.0\Library\bin")
    for i in range(len(image)):
        image[i].save(path+composer+"\\"+composition+" "+str(i+1)+'.jpg', 'JPEG')


def imslp_safe(url):
    '''
    IMSLP score URLs are in the format https://imslp.org/wiki/composition(LastName,_FirstName_MiddleNames)
    where special characters are preserved.
    The URL provided by valid_link in get_pdf() is DOUBLE ENCODED. This
    function replaces any occurences of %25 to remove the double encoding.

    Raw brackets caused errors in my test runs so I've replaced them with
    their respective escape sequences to avoid errors.
    '''
    url = url.replace("(", "%28")
    url = url.replace(")", "%29")
    url = url.replace("%25", "%")
    return url


def get_pdf(composer, compositions):
    # set up Chrome driver options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # run the browser in the background
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    # set up Chrome driver with the path to the chromedriver executable
    driver_path = r'C:\Users\rin\Documents\chromedriber\chromedriver.exe'
    driver = webdriver.Chrome(driver_path, options=chrome_options)

    for composition_name in compositions:
        query = f'site:imslp.org {composition_name}'
        query = query.replace(" ", "%20")
        url = f'https://www.google.com/search?q={query}'
        time.sleep(5)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        try:
            imslp_link = soup.find('a', href=lambda href: href and composer in href.lower() and href[:24]=="/url?q=https://imslp.org")['href']
        except:
            if "unusual traffic" in response.text:
                print(f"{composer}- {composition_name}\t|\tUnusual traffic detected. Stopping process.")
                break
            else:
                print(f"{composer}- {composition_name}\t|\tSite not found. Skipping")
                continue
        valid_link = imslp_link.split("&sa")
        valid_link = imslp_safe(valid_link[0][7:])
        time.sleep(2)
        driver.get(valid_link+"#tabScore1")

        if "site ripping ban" in driver.find_element(By.TAG_NAME, "body").text:
            time_now = time.strftime("%H:%M:%S", time.localtime())
            print(f"{composer}- {composition_name}\t|\tBan applied at IMSLP @ {time_now}")
            break

        '''
        Search for "Complete Score (scan) and go to the link containing it"
        In case of no cookies/fresh session, a disclaimer page will pop up. If statement will handle it.
        Wait 15 seconds for download link to be generated, additional 2 seconds for buffer
        '''
        try:
            driver.find_element('xpath', "//a[.//span[text()='Complete Score (scan)']]").click()
        except:
            try:
                driver.find_element('xpath', "//a[.//span[text()='Complete Score']]").click()
            except:
                print(f'{composer}- {composition_name}\t|\tComplete score not found, skipping')
                continue

        if driver.title == "Disclaimer - IMSLP: Free Sheet Music PDF Download":
            driver.find_element(By.LINK_TEXT, "I accept this disclaimer, continue to download file").click()
        elif driver.title != "Subscribe - IMSLP: Free Sheet Music PDF Download":
            print(f'{composer}- {composition_name}\t|\t{driver.title} page encountered. Skipping.')
            break
        time.sleep(20)

        try:
            download_link = driver.find_element('xpath', "//a[.='Click here to continue your download.']")
        except:
            print(f'{composer}- {composition_name}\t|\tDownload link not found.')
            break
        pdf_url = download_link.get_attribute('href')
        response = requests.get(pdf_url)
        with open(f'{path}{composer}\\{composition_name}.pdf', 'wb') as f:
            f.write(response.content)

        to_image(composer, composition_name)
        print(f'{composer}- {composition_name}\t|\t Downloaded and converted to image.')
    # quit the browser
    driver.quit()


# run the script simulaneously for each composer
threads = [Thread(target = get_pdf, args=(c, compositions[c], )) for c in compositions]
for t in threads:
    t.start()

for t in threads:
    t.join()
