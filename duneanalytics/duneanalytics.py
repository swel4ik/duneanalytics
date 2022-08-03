# -*- coding: utf-8 -*- #
"""This provides the DuneAnalytics class implementation"""
from dydx3 import Client
from requests import Session, get
import logging
import pandas as pd
import os
from boto3 import session
from botocore.client import Config

# --------- Constants --------- #

BASE_URL = "https://dune.com"
GRAPH_URL = 'https://core-hsr.duneanalytics.com/v1/graphql'


# --------- Constants --------- #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s : %(levelname)s : %(funcName)-9s : %(message)s'
)
logger = logging.getLogger("dune")


class DuneAnalytics:
    """
    DuneAnalytics class to act as python client for duneanalytics.com.
    All requests to be made through this class.
    """

    def __init__(self, username, password, ACCESS_ID, SECRET_KEY):
        """
        Initialize the object
        :param username: username for duneanalytics.com
        :param password: password for duneanalytics.com
        """
        self.csrf = None
        self.auth_refresh = None
        self.token = None
        self.query_id = None
        self.username = username
        self.password = password
        self.ACCESS_ID = ACCESS_ID
        self.SECRET_KEY = SECRET_KEY
        self.session = Session()

        self.s3_session = session.Session()
        self.s3_client = self.s3_session.client('s3',
                                                region_name='nyc3',
                                                endpoint_url='https://nyc3.digitaloceanspaces.com',
                                                aws_access_key_id=self.ACCESS_ID,
                                                aws_secret_access_key=self.SECRET_KEY)

        self.s3_resource = self.s3_session.resource('s3',
                                                    region_name='nyc3',
                                                    endpoint_url='https://nyc3.digitaloceanspaces.com',
                                                    aws_access_key_id=self.ACCESS_ID,
                                                    aws_secret_access_key=self.SECRET_KEY)
        self.s3_space = self.s3_resource.Bucket('dydx-csv')
        self.dydx_client = Client(host='https://api.dydx.exchange')
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                      'image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'dnt': '1',
            'sec-ch-ua': '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'origin': BASE_URL,
            'upgrade-insecure-requests': '1'
        }
        self.session.headers.update(headers)

    def login(self):
        """
        Try to login to duneanalytics.com & get the token
        :return:
        """
        login_url = BASE_URL + '/auth/login'
        csrf_url = BASE_URL + '/api/auth/csrf'
        auth_url = BASE_URL + '/api/auth'

        # fetch login page
        self.session.get(login_url)

        # get csrf token
        self.session.post(csrf_url)
        self.csrf = self.session.cookies.get('csrf')

        # try to login
        form_data = {
            'action': 'login',
            'username': self.username,
            'password': self.password,
            'csrf': self.csrf,
            'next': BASE_URL
        }

        self.session.post(auth_url, data=form_data)
        self.auth_refresh = self.session.cookies.get('auth-refresh')
        if self.auth_refresh is None:
            logger.warning("Login Failed!")

    def fetch_auth_token(self):
        """
        Fetch authorization token for the user
        :return:
        """
        session_url = BASE_URL + '/api/auth/session'

        response = self.session.post(session_url)
        if response.status_code == 200:
            self.token = response.json().get('token')
            if self.token is None:
                logger.warning("Fetching Token Failed!")
        else:
            logger.error(response.text)

    def query_result_id(self, query_id):
        """
        Fetch the query result id for a query

        :param query_id: provide the query_id
        :return:
        """
        self.query_id = query_id
        query_data = {"operationName": "GetResult", "variables": {"query_id": query_id},
                      "query": "query GetResult($query_id: Int!, $parameters: [Parameter!]) "
                               "{\n  get_result_v2(query_id: $query_id, parameters: $parameters) "
                               "{\n    job_id\n    result_id\n    error_id\n    __typename\n  }\n}\n"
                      }

        self.session.headers.update({'authorization': f'Bearer {self.token}'})

        response = self.session.post(GRAPH_URL, json=query_data)
        if response.status_code == 200:
            data = response.json()
            logger.debug(data)
            if 'errors' in data:
                logger.error(data.get('errors'))
                return None
            result_id = data.get('data').get('get_result_v2').get('result_id')
            return result_id
        else:
            logger.error(response.text)
            return None

    def query_result(self, result_id):
        """
        Fetch the result for a query
        :param result_id: result id of the query
        :return:
        """
        query_data = {"operationName": "FindResultDataByResult",
                      "variables": {"result_id": result_id, "error_id": "00000000-0000-0000-0000-000000000000"},
                      "query": "query FindResultDataByResult($result_id: uuid!, $error_id: uuid!) "
                               "{\n  query_results(where: {id: {_eq: $result_id}}) "
                               "{\n    id\n    job_id\n    runtime\n    generated_at\n    columns\n    __typename\n  }"
                               "\n  query_errors(where: {id: {_eq: $error_id}}) {\n    id\n    job_id\n    runtime\n"
                               "    message\n    metadata\n    type\n    generated_at\n    __typename\n  }\n"
                               "\n  get_result_by_result_id(args: {want_result_id: $result_id}) {\n    data\n    __typename\n  }\n}\n"
                      }

        self.session.headers.update({'authorization': f'Bearer {self.token}'})

        response = self.session.post(GRAPH_URL, json=query_data)
        if response.status_code == 200:
            data = response.json()
            logger.debug(data)
            return data
        else:
            logger.error(response.text)
            return {}

    def query2csv(self, query_data, save_path):
        keys = query_data['data']['get_result_by_result_id'][0]['data'].keys()
        json_data = {}

        for key in keys:
            json_data[key] = []

        for row in query_data['data']['get_result_by_result_id']:
            for key in json_data.keys():
                json_data[key].append(row['data'][key])

        csv_data = pd.DataFrame(json_data)
        csv_data.to_csv(os.path.join(save_path, f'{self.query_id}.csv'))

    def download_csv(self, result_id, save_path='./'):
        """
        Fetch the query result id for a query

        :param query_id: provide the query_id
        :return:
        """
        download_data = {"operationName": "DownloadQuery",
                         "variables": {"result_id": result_id},
                         "query": "query DownloadQuery($result_id: uuid!) {\n  download_csv(result_id: $result_id) {\n    url\n    __typename\n  }\n}\n"
                         }

        self.session.headers.update({'authorization': f'Bearer {self.token}'})

        response = self.session.post(GRAPH_URL, json=download_data)
        if response.status_code == 200:
            data = response.json()
            logger.debug(data)
            if 'errors' in data:
                logger.error(data.get('errors'))
                return None

            csv_url = data['data']['download_csv']['url']
            response = get(csv_url)
            if response.status_code == 200:
                with open(os.path.join(save_path, f'{self.query_id}.csv'), "wb") as handle:
                    for data in response.iter_content():
                        handle.write(data)
            else:
                logger.error(response.text)
                return None
        else:
            logger.error(response.text)
            return None

    def s3_upload(self, csv_path):
        save_path = csv_path.split('/')[-1]
        self.s3_client.upload_file(csv_path, 'dydx-csv', save_path)
        current_csv = self.s3_resource.Bucket('dydx-csv').Object(save_path)
        current_csv.Acl().put(ACL='public-read')

    def dune2space(self,  result_id, save_path='./'):
        self.download_csv(result_id=result_id, save_path=save_path)
        self.s3_upload(csv_path=os.path.join(save_path, f'{self.query_id}.csv'))
        os.remove(os.path.join(save_path, f'{self.query_id}.csv'))

    def update_permissions(self):
        bucket = self.s3_resource.Bucket('dydx-csv')
        for bucket_object in bucket.objects.all():
            bucket_object.Acl().put(ACL='public-read')
    # DYDX exchange API

    def get_current_price(self, asset: str, save_path: str = './'):
        markets = self.dydx_client.public.get_markets()
        data = markets.data['markets'][f'{asset}-USD']['indexPrice']
        with open(f'{os.path.join(save_path, asset)}.csv', 'w') as f:
            f.write('price\n')
            f.write(data)

    def dydx2space(self, asset: str, save_path: str = './'):
        self.get_current_price(asset=asset, save_path=save_path)
        self.s3_upload(csv_path=os.path.join(save_path, f'{asset}.csv'))