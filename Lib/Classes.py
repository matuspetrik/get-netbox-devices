import re
import yaml
import sys
import logging
import os
import urllib3
import requests
from requests.exceptions import ConnectionError
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import Lib.Functions as fns
from pprint import pprint as pp
from jinja2 import Environment, FileSystemLoader

class Logger:
    def __init__(self, name=__name__, log_file='app.log',
                 file_level=logging.DEBUG, console_level=logging.INFO):
        """
        Initialize the logger.

        :param name: Logger name (usually __name__ of the module)
        :param log_file: Path to the log file
        :param file_level: Logging level for the file handler
        :param console_level: Logging level for the console handler
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels; handlers filter further

        # Prevent adding multiple handlers if logger already configured
        if not self.logger.hasHandlers():
            # File handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(file_level)
            file_formatter = logging.Formatter(
                "[%(asctime)s::%(filename)s::%(lineno)d::%(funcName)s()] %(levelname)s: %(message)s", 
                    datefmt='%Y-%m-%dT%H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)

            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_formatter = logging.Formatter(
                '%(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)

            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        """Return the configured logger instance."""
        return self.logger
# initialize Logger after Class definition
log = Logger().get_logger()

class Utils:

    def __init__(self):
        pass

    def check_ip_online(self, ip):
        print(f"NOTE: Pinging { ip }")
        response = os.system(f"ping -c 1 -q { ip }")
        return response == 0


class Vars:

    def __init__(self, input_file="Var/input.yml"):
        try:
            with open(input_file, 'r') as file:
                self.data = yaml.safe_load(file)
        except Exception as e:
            log.info(e)

    def get_vars(self):
        return self.data


class Netbox:

    def __init__(self, **kwargs):
        self.args = fns.munchify(**kwargs)

        # Replace placeholders with system environment variables
        self.args.netbox.ipv4 = os.environ.get('NETBOX_IPV4')
        self.args.netbox.host = os.environ.get('NETBOX_FQDN')
        self.args.netbox.token_ro = os.environ.get('NETBOX_TOKEN_RO')
        self.args.output_file_path = os.environ.get('OUTPUT_FILE_PATH')

        # Continue
        self.url = f"https://{self.args.netbox.host}/api"
        self.token = self.args.netbox.token_ro
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.session = requests.Session()

    def __enter__(self):
        log.info("Entering the context - [OK]")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # log = Logger().get_logger()
        if exc_type:
            log.info(f"Exception caught - [NOK]: {exc_type.__name__} - {exc_value}")
        else:
            log.info("Closing API session - [OK]")
            # Close the API session
            self.session.close()
        # Returning False propagates the exception, True suppresses it
        return False

    def get_criteria(self):
        ''' Input: criteria read from Var/input.yml file,
            using path `criteria_input/input:
            criteria_input:
                input:
                    platform:
                    - fortigate
                    - mikrotik
                    - ios
                    - ios-xe
                    - ios-firmware
                    - asa
                    status:
                    - active
                    region:
                    - slovakia
                    has_primary_ip:
                    - true
                    exclude_tags:
                    - schenck
                    - technology
            Return dict:
            {
                'exclude_tags': ['schenck', 'technology'],
                'has_primary_ip': [True],
                'platform': ['fortigate', 'mikrotik', 'ios', 'ios-xe', 'ios-firmware', 'asa'],
                'region': ['slovakia'],
                'status': ['active'], 
                'individual_hosts': ['nd-idc-fw01']
            }
        '''
        criteria_dict = {}
        for crit_key, crit_vals in self.args.criteria_input.input.items():
            criteria_dict[crit_key] = []
            for crit_val in crit_vals:
                criteria_dict[crit_key].append(crit_val)
        # log.info(criteria_dict)
        return criteria_dict

    def catenate_url_suffix(self, criteria_dict):
        ''' Catenate final URL string to be attached to Netbox API url.
            Input: criteria dict
            Output: url_suffix with filtered criteria
            Eg. platform=fortigate&platform=mikrotik&platform=ios&platform=ios-xe\
                &platform=ios-firmware&platform=asa&status=active&region=slovakia\
                &has_primary_ip=True&tag__n=schenck&tag__n=technology
        '''
        url_list = []
        for crit_keys, crit_vals in criteria_dict.items():
            for value in crit_vals:
                # if crit_keys != 'individual_hosts':
                    url_list.append(f"{crit_keys}={value}")
                # else:
                #     url_list.append(f"q={value}")
        url_suffix = "&".join(url_list)
        log.info(f"{url_suffix}")
        return url_suffix

    def catenate_final_url(self, *args):
        ''' Input: any number of strings.
            Output: input strings joined by '?'
        '''
        list_of_strings = []
        for string in args:
            list_of_strings.append(string)
        final_url = "?".join(list_of_strings)
        log.info(f"Final URL: { final_url }")
        return f"{final_url}"

    def get_platforms(self):
        criteria_dict = {}
        for crit_key, crit_vals in self.args.criteria_input.input.items():
            if crit_key == "platform":
                log.info(f"Platforms: { crit_vals }")
                return crit_vals

    def orchestrate_output_file_creation(self):
        ''' Orchestrate the final file creation:
            - Read the criteria dictionary form Var/input.yml
            - Generate the filtering api url string
            - Pull the data from Netbox
            - Process the data through Jinja2 template
            - Generate final file, if Netbox is ok, use previous file instead
        '''
        # - Read the criteria dictionary form Var/input.yml
        criteria_dict = self.get_criteria()
        # - Generate the filtering api url string
        url_suffix = self.catenate_url_suffix(criteria_dict)
        dcim_devices_url = f"{self.url}/dcim/devices"
        final_url = self.catenate_final_url(dcim_devices_url, url_suffix)

        # - Pull the data from Netbox for individual hostnames only
        if criteria_dict['individual_hosts']:
            url_suffix = self.catenate_url_suffix(criteria_dict)
            final_url = self.catenate_final_url(dcim_devices_url, url_suffix)
            while self.args.counter > 0:
                try:
                    response = self.session.get(final_url, headers=self.headers, verify=False)
                    log.info(f"Netbox session response: { response.status_code }")
                    response_munch = fns.munchify(**response.json())
                    # log.info(response_munch.results)
                except ConnectionError:
                    log.info(f"Netbox not reachable at { self.args.netbox.host }. "
                            f"Falling back to IP address using system env var NETBOX_FQDN")
                    log.info(f"Connection attempts to Netbox: { self.args.counter } left.")
                    self.args.counter -= 1
                    self.url = f"https://{self.args.netbox.ipv4}/api"
                    self.orchestrate_output_file_creation()
                except Exception as e:
                    # log.info(e)
                    self.args.counter -= 1
                    log.info(f"Failed getting url response from Netbox. "\
                            f"Leaving file '{ self.args.output_file_path }' from prev. run.")
                else:
                    self.args.counter = 0
                    # - Process the data through Jinja2 template
                    platforms = self.get_platforms()
                    env = Environment(loader=FileSystemLoader('Template'),
                                    keep_trailing_newline=True)
                    template = env.get_template('hostfile.j2')
                    output = template.render(results=response_munch.results, platforms=platforms)

        # # - Pull the data from Netbox
        # while self.args.counter > 0:
        #     try:
        #         response = self.session.get(final_url, headers=self.headers, verify=False)
        #         log.info(f"Netbox session response: { response.status_code }")
        #         response_munch = fns.munchify(**response.json())
        #     except ConnectionError:
        #         log.info(f"Netbox not reachable at { self.args.netbox.host }. "
        #                  f"Falling back to IP address using system env var NETBOX_FQDN")
        #         log.info(f"Connection attempts to Netbox: { self.args.counter } left.")
        #         self.args.counter -= 1
        #         self.url = f"https://{self.args.netbox.ipv4}/api"
        #         self.orchestrate_output_file_creation()
        #     except Exception as e:
        #         # log.info(e)
        #         self.args.counter -= 1
        #         log.info(f"Failed getting url response from Netbox. "\
        #                 f"Leaving file '{ self.args.output_file_path }' from prev. run.")
        #     else:
        #         self.args.counter = 0
        #         # - Process the data through Jinja2 template
        #         platforms = self.get_platforms()
        #         env = Environment(loader=FileSystemLoader('Template'),
        #                         keep_trailing_newline=True)
        #         template = env.get_template('hostfile.j2')
        #         output = template.render(results=response_munch.results, platforms=platforms)

        #         # - Generate final file, if Netbox is ok, use previous file instead
        #         with open(self.args.output_file_path, 'w') as file:
        #             log.info(f"Writing Jinja output to file: { self.args.output_file_path }")
        #             file.write(output)
        #             log.info(f"Success getting url response from Netbox. "\
        #                     f"Writing new file '{ self.args.output_file_path }'.")