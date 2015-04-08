from collections import namedtuple
import re
import requests
from requests_ntlm import HttpNtlmAuth
from bs4 import BeautifulSoup

BASE_URL = 'https://uniflow.calvin.edu/'
CLIENT_PATH = 'pwclient/'
RQM_PATH = 'pwrqm/'
AUTH_PATH = 'getuserid.asp'
PRINT_BUDGET_PATH = 'dispBudget.asp'
PRINT_QUEUE_PATH = 'dispObjects.asp'

def get_uniflow_client(username, password):
    return _UniflowClient(username, password)


class _UniflowClient:
    def __init__(self, username, password):
        if username is None or username == '':
            # blank user name leads to an invalid ntlm domain
            raise InvalidCredentialsError('User name must not be blank.')

        self._username = username
        self._password = password
        self._budget_scraper = _BudgetScraper()
        self._queue_scraper = _QueueScraper()
        # Verify the credentials
        self._budget_scraper.sign_in(self._username, self._password)
        self._queue_scraper.sign_in(self._username, self._password)

    def get_budget(self):
        self._budget_scraper.sign_in(self._username, self._password)
        return self._budget_scraper.fetch_data()

    def get_print_queue(self):
        self._queue_scraper.sign_in(self._username, self._password)
        return self._queue_scraper.fetch_data()

    def delete_print_jobs(self, job_ids):
        self._queue_scraper.sign_in(self._username, self._password)
        self._queue_scraper.delete_print_jobs(job_ids)

PrintJob = namedtuple('PrintJob',['job_id', 'name', 'pages', 'copies',
                                  'price', 'printer_name', 'date'])

class _PrintScraper:
    """Parent class of BudgetScraper and QueueScraper.
    """
    
    def sign_in(self, path, username, password):
        domain = ''
        try:
            self._session.get(BASE_URL + path)
            self._session.auth = HttpNtlmAuth(domain + '\\' + username,
                                              password, self._session)
            post_data = {'theAction': 'ntlogin'}
            response = self._session.post(BASE_URL + path + AUTH_PATH,
                                          data=post_data)
        except requests.exceptions.ConnectionError as err:
            raise NetworkError(err)
        except requests.exceptions.HTTPError as err:
            raise NetworkError(err)
        except requests.exceptions.RequestException as err:
            raise NetworkError(err)

        if response.status_code != requests.codes.ok:
            raise InvalidCredentialsError
        self.update_token(response.text)


class _BudgetScraper(_PrintScraper):
    """Stores a session with print.calvin.edu/pwclient, and a token.
    """

    def __init__(self):
        self.path = CLIENT_PATH
        self._session = requests.Session()

    def update_token(self, text):
        match = re.search(r"\.c_updateToken\(\"(.*)\"\)", text)
        if match is not None:
            self._token = match.group(1)
            return
        raise ScrapingError("No token found.")

    def sign_in(self, username, password):
        _PrintScraper.sign_in(self, self.path, username, password)
    
    def fetch_data(self):
        """Returns the budget of the user.
        """
        query_parameters = {
            'mmtype': 'budget',
            'smtype': '',
            'token': self._token
        }

        try:
            response = self._session.get(BASE_URL + self.path + PRINT_BUDGET_PATH,
                                         params=query_parameters)
        except requests.exceptions.ConnectionError as err:
            raise NetworkError(err)
        except requests.exceptions.HTTPError as err:
            raise NetworkError(err)
        except requests.exceptions.RequestException as err:
            raise NetworkError(err)
        if response.status_code != requests.codes.ok:
            raise ScrapingError("Invalid HTTP status code: {}".format(response.status_code))
        soup = BeautifulSoup(response.text, 'lxml')
        title = soup.find('title')
        if title is None:
            raise ScrapingError("Page has no title.")
        budget_tag = soup.find('font', class_= 'editHeadline')
        parent_tag = soup.find('font', class_= 'editHeadline').parent
        match = re.search(r"Your current budget is:", str(parent_tag))
        if match is None:
            raise ScrapingError("Budget not found.")
        try:
            budget = float(budget_tag.string)
        except ValueError:
            raise ScrapingError("Budget is not a valid float: {}".format(budget_tag.string))
        return budget


class _QueueScraper(_PrintScraper):
    """Stores a session with print.calvin.edu/pwrqm, and a token.
    """
    def __init__(self):
        self.path = RQM_PATH
        self._session = requests.Session()

    def sign_in(self, username, password):
        _PrintScraper.sign_in(self, self.path, username, password)

    def update_token(self, text):
        match = re.search(r"token=(.*)\";", text)
        if match is not None:
            self._token = match.group(1)
            return
        raise ScrapingError("No token found.")
    
    def fetch_data(self):
        """Returns a list of _PrintJob objects to represent a user's print queue."""
        query_parameters = {
            'mmtype': 'login',
            'smtype': '',
            'token': self._token
        }

        try:
            response = self._session.get(BASE_URL + self.path + PRINT_QUEUE_PATH,
                                         params=query_parameters)
        except requests.exceptions.ConnectionError as err:
            raise NetworkError(err)
        except requests.exceptions.HTTPError as err:
            raise NetworkError(err)
        except requests.exceptions.RequestException as err:
            raise NetworkError(err)
        if response.status_code != requests.codes.ok:
            raise ScrapingError("Invalid HTTP status code: {}".format(response.status_code))
        soup = BeautifulSoup(response.text, 'lxml')
        #TODO: Come up with a better way for checking for scraping errors
        title = soup.find('title')
        if title is None:
            raise ScrapingError("Page has no title.")
        print_job_tags = soup.select('#divMain tr td.Middle')
        print_jobs = []
        numberOfJobs = len(print_job_tags) / 7
        for i in range(numberOfJobs):
            j = i * 7
            try:
                job_id = re.search(r"c_OnSelectJob\('(.*)'\)", unicode(print_job_tags[0 + j]['onclick'])).group(1)
                name = unicode(print_job_tags[0 + j].string)
                pages = int(print_job_tags[1 + j].string)
                copies = int(print_job_tags[2 + j].string)
                price = float(print_job_tags[3 + j].string)
                printer_name = unicode(print_job_tags[4 + j].string)
                date = unicode(print_job_tags[6 + j].string)
            except IndexError as err:
                raise ScrapingError(err)
            except ValueError as err:
                raise ScrapingError(err)
            if job_id is None:
                raise ScrapingError("Print job id not found for document: {}".format(name))
            print_jobs.append(PrintJob(job_id, name, pages, copies, price, printer_name, date))
        return print_jobs

    def delete_print_jobs(self, job_ids):
        """Deletes print jobs from a user's print queue."""
        post_data = {
            'theaction': 'search',
            'mmtype': 'login',
            'smtype': '',
            'theItems': 'selected',
            'Action_IncReleaseQueue': 'Delete',
            'token': self._token
        }

        for job_id in job_ids:
            post_data[job_id] = 'yes'

        try:
            response = self._session.post(BASE_URL + self.path + PRINT_QUEUE_PATH,
                                          data=post_data)
        except requests.exceptions.ConnectionError as err:
            raise NetworkError(err)
        except requests.exceptions.HTTPError as err:
            raise NetworkError(err)
        except requests.exceptions.RequestException as err:
            raise NetworkError(err)
        if response.status_code != requests.codes.ok:
            raise ScrapingError("Invalid HTTP status code: {}".format(response.status_code))


class ScrapingError(Exception):
    pass

class NetworkError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass
