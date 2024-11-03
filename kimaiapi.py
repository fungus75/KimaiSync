import requests


class KimaiAPI:
    def __init__(self, url=None, apikey=None):
        self.__logged_on = False
        self.__apikey = apikey
        self.__url = url

    def login(self, url=None, apikey=None):
        # overwrite stored parameters
        if url is not None:
            self.__url = url
        if apikey is not None:
            self.__apikey = apikey

        # try to login to server
        return self.__get_from_server("ping")

    def get_customer(self, id=None, term=None):
        if not self.__logged_on:
            raise Exception("You have to logon first")

    def __get_from_server(self, endpoint):
        # verify parameter
        if self.__url is None:
            raise Exception("URL not given/defined")
        if self.__apikey is None:
            raise Exception("APIKEY not given/defined")

        url = self.__url
        if not url.endswith("/"):
            url += "/"
        url += "api/" + endpoint

        headers = {"Authorization": "Bearer " + self.__apikey}
        r = requests.get(url, headers=headers)
        if r.status_code == 401:
            raise Exception("Wrong API Key")
