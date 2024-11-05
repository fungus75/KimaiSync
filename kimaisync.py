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


project_list = None
activity_list = None


def ask_project_mapping(project, api):
    global project_list
    print("Please provide Mapping for " + project["name"])
    if project_list is None:
        project_list = api.get_projects()

    possible_ids = ["-1"]

    for p in project_list:
        print(p["id"], p["name"])
        possible_ids.append(str(p["id"]))

    while True:
        res = input("Mapping-ID for project " + project["name"] + " (-1 = Do not map): ")
        if res in possible_ids:
            return res


def save_updated_config(config, file):
    if "updated" in config:
        config.pop('updated', None)
        with open(file, 'w') as f:
            json.dump(config, f)


def ask_activity_mapping(activity, api):
    global activity_list
    print("Please provide Mapping for " + activity["name"])
    if activity_list is None:
        activity_list = api.get_activities(order="id")

    possible_ids = []

    for p in activity_list:
        print(p["id"], p["name"])
        possible_ids.append(str(p["id"]))

    while True:
        res = input("Mapping-ID for activity " + activity["name"] + ": ")
        if res in possible_ids:
            return res


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
    save_updated_config(config, args.config_file)

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
    if "project_mapping" not in config:
        config["project_mapping"] = {}
    if "activity_mapping" not in config:
        config["activity_mapping"] = {}
    project_mapping = config["project_mapping"]
    activity_mapping = config["activity_mapping"]
    for project in projects:
        if str(project["id"]) not in project_mapping:
            print("Mapping missing for project " + project["name"])
            config["project_mapping"][str(project["id"])] = ask_project_mapping(project, dest_api)
            config["updated"] = True
            save_updated_config(config, args.config_file)

        activities = src_api.get_activities(project_id=project["id"])
        for activity in activities:
            if str(activity["id"]) not in activity_mapping:
                print("Mapping missing for activity " + activity["name"])
                config["activity_mapping"][str(activity["id"])] = ask_activity_mapping(activity, dest_api)
                config["updated"] = True
                save_updated_config(config, args.config_file)

    # start syncing at last "end"
    begin = None
    last_source_id = None
    if "last_begin" in config:
        begin = config["last_begin"]
        if '+' in begin:
            begin = begin.split('+', 1)[0]
    if "last_source_id" in config:
        last_source_id= config["last_source_id"]

    timesheets = src_api.get_timesheets(customer_id=customer["id"], order="begin", direction="ASC", begin=begin)
    for timesheet in timesheets:
        # only complete elements
        if "end" not in timesheet or timesheet["end"] == "":
            continue

        source_id = timesheet["id"]
        if last_source_id is not None and source_id<=last_source_id:
            continue

        # remove some unnecessary fields
        timesheet.pop('user', None)
        timesheet.pop('id', None)
        timesheet.pop('tags', None)
        timesheet.pop('duration', None)
        timesheet.pop('rate', None)
        timesheet.pop('internalRate', None)
        timesheet.pop('metaFields', None)



        # translate mapping
        timesheet["activity"] = activity_mapping[str(timesheet["activity"])]
        timesheet["project"] = project_mapping[str(timesheet["project"])]

        # Save Timesheet in Destination
        dest_api.save_timesheet(timesheet)
        if args.verbose:
            print(timesheet)

        # Save Begin-Date in config in case of a crash/restart
        config["last_begin"] = timesheet["begin"]
        config["last_source_id"] = source_id
        config["updated"] = True
        save_updated_config(config, args.config_file)
