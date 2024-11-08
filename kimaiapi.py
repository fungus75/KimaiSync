import json
import urllib.parse

import requests


class KimaiAPI:
    def __init__(self, url=None, apikey=None):
        self.__logged_on = False
        self.__api_status_code = None
        self.__apikey = apikey
        self.__url = url

    def login(self, url=None, apikey=None):
        # overwrite stored parameters
        if url is not None:
            self.__url = url
        if apikey is not None:
            self.__apikey = apikey

        # try to login to server
        x = self.__get_from_server("ping")
        self.__logged_on = True

    def get_customer(self, id=None, term=None):
        if not self.__logged_on:
            raise Exception("You have to logon first")
        if id is not None:
            return self.__get_from_server("customers/" + str(id))
        if term is not None:
            return self.__get_first_of_array(self.__get_from_server("customers?term=" + urllib.parse.quote_plus(term)))
        raise Exception("No valid parameter supplied")

    def get_projects(self, id=None, customer_id=None):
        if not self.__logged_on:
            raise Exception("You have to logon first")
        if id is not None:
            return self.__get_from_server("projects/" + str(id))
        if customer_id is not None:
            return self.__get_from_server("projects?customer=" + str(customer_id))
        return self.__get_from_server("projects")

    def get_activities(self, id=None, project_id=None, order=None):
        if not self.__logged_on:
            raise Exception("You have to logon first")
        query = "activities"

        if id is not None:
            query = "activities/" + str(id)
        if project_id is not None:
            query = "activities?project=" + str(project_id)

        if order is not None:
            if "?" in query:
                query += "&"
            else:
                query += "?"
            query += "orderBy=" + order

        return self.__get_from_server(query)

    def get_timesheets(self, id=None, customer_id=None, project_id=None, order=None, direction=None, begin = None):
        if not self.__logged_on:
            raise Exception("You have to logon first")
        query = "timesheets"
        if id is not None:
            query = "timesheets/" + str(id)
        if customer_id is not None:
            query = "timesheets?customer=" + str(customer_id)
        if project_id is not None:
            query = "timesheets?project=" + str(project_id)

        if order is not None:
            if "?" in query:
                query += "&"
            else:
                query += "?"
            query += "orderBy=" + order

        if begin is not None:
            if "?" in query:
                query += "&"
            else:
                query += "?"
            query += "begin=" + begin


        if direction is not None:
            if "?" in query:
                query += "&"
            else:
                query += "?"
            query += "order=" + direction

        return self.__get_from_server(query)

    def save_timesheet(self, timesheet):
        if "id" in timesheet:
            endpoint = "timesheets/"+str(timesheet["id"])
            timesheet.pop('id', None)
            return self.__patch_to_server(endpoint, timesheet)

        return self.__post_to_server("timesheets", timesheet)

    def __get_from_server(self, endpoint):
        return self.__apicall(endpoint)

    def __apicall(self,endpoint,post=None, patch = None):
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
        if post is None and patch is None:
            r = requests.get(url, headers=headers)
        elif post is not None:
            r = requests.post(url, headers=headers, json=post)
        elif patch is not None:
            r = requests.patch(url, headers=headers, json=patch)
        self.__api_status_code = r.status_code
        if r.status_code == 401:
            raise Exception("Wrong API Key")

        if r.status_code != 200:
            raise Exception("Other API Exception, statuscode = " + str(r.status_code))

        # return as json object
        return json.loads(r.text)

    def __post_to_server(self, endpoint, data):
        return self.__apicall(endpoint, post=data)

    def __patch_to_server(self, endpoint, data):
        return self.__apicall(endpoint, patch=data)


    def __get_first_of_array(self, data):
        if data == None:
            return data

        if hasattr(data, "__len__"):
            if len(data) == 0:
                return None
            return data[0]

        return data
