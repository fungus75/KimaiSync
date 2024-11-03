import argparse
import json
from inspect import getsourcefile
import os
import sys

from kimaiapi import KimaiAPI

default_config_file = 'kimaisync.cfg.json'


def get_config_value(name, config, args):
    args_dict = vars(args)
    if name in args_dict and args_dict.get(name) is not None:
        config["updated"] = True
        config[name] = args_dict.get(name)
        return

    if name in config:
        return

    if args.non_interactive:
        sys.exit("Error: Config Parameter " + name + " unknown")

    config[name] = input("Please enter value for parameter " + name + ": ")
    config["updated"] = True


def is_empty(data):
    if data is None:
        return True

    if hasattr(data, "__len__"):
        if len(data) == 0:
            return True

    return False


if __name__ == "__main__":
    script_full_path = os.path.abspath(getsourcefile(lambda: 0))
    script_full_folder = os.path.dirname((script_full_path))
    default_config_fullpath = os.path.join(script_full_folder, default_config_file)
    # Command-Line Parser
    parser = argparse.ArgumentParser(description='Kimai Sync Script')
    parser.add_argument('-su', '--source_url',
                        help='Full URL of the source Kimai Installation')
    parser.add_argument('-sa', '--source_apikey',
                        help='API Key for the source Kimai Installation')
    parser.add_argument('-sc', '--source_customer',
                        help='Source Customer name')
    parser.add_argument('-du', '--destination_url',
                        help='Full URL of the destination Kimai Installation')
    parser.add_argument('-da', '--destination_apikey',
                        help='API Key for the destination Kimai Installation')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose mode')
    parser.add_argument('-ni', '--non_interactive', action='store_true',
                        help='Non Interactive mode')
    parser.add_argument('-c', '--config_file',
                        default=default_config_fullpath,
                        help='Full path of config file, default: ' + default_config_fullpath)

    args = parser.parse_args()

    # load config from file
    if args.config_file is None or not os.path.exists(args.config_file):
        config = {}
    else:
        with open(args.config_file) as json_data:
            config = json.load(json_data)

    # replace config with parameters or ask user
    get_config_value("source_url", config, args)
    get_config_value("source_apikey", config, args)
    get_config_value("source_customer", config, args)
    get_config_value("destination_url", config, args)
    get_config_value("destination_apikey", config, args)

    # save updated config
    if "updated" in config:
        config.pop('updated', None)
        with open(args.config_file, 'w') as f:
            json.dump(config, f)

    # logon to destination api
    dest_api = KimaiAPI(url=config["destination_url"], apikey=config["destination_apikey"])
    dest_api.login()

    # logon to source api
    src_api = KimaiAPI(url=config["source_url"], apikey=config["source_apikey"])
    src_api.login()

    # validate customer
    customer = src_api.get_customer(term=config["source_customer"])
    if is_empty(customer):
        raise Exception("Error: source_customer " + config["source_customer"] + " not found")

    # validate projects and mapping
    projects = src_api.get_projects(customer_id=customer["id"])
    if not "project_mapping" in config:
        config["project_mapping"] = []
    if not "activity_mapping" in config:
        config["activity_mapping"] = []
    project_mapping = config["project_mapping"]
    activity_mapping= config["activity_mapping"]
    for project in projects:
        if project["id"] not in project_mapping:
            print("Mapping missing for project " + project["name"])
            # TODO: Create Mapping

        activities = src_api.get_activities(project_id=project["id"])
        for activity in activities:
            if activity["id"] not in activity_mapping:
                print("Mapping missing for activity " + activity["name"])
                # TODO: Create Mapping

