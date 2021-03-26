#!interpreter

"""
This program is designed to redirect docker container logs into a centralized directory.
"""

# Built-in/Generic Imports
import os
import sys
import time
import traceback
from datetime import datetime
import threading
from threading import Thread
from threading import Event
import subprocess
import io

# Libraries
from ictools.directors.thread_director import start_function_thread
from ictools.directors.yaml_director import read_yaml_config
from ictools.directors.yaml_director import yaml_value_validation
from ictools.directors.log_director import create_logger
from ictools.directors.email_director import send_email
from functools import partial

__author__ = 'IncognitoCoding'
__copyright__ = 'Copyright 2021, docker_log_redirect'
__credits__ = ['IncognitoCoding']
__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'IncognitoCoding'
__status__ = 'Development'


def get_docker_log(container_name, container_logger, root_logger):
    """
    Runs a sub-process command to redirect the log output for the docker container.

    Args:
        container_name (str): docker container name
        container_logger (logger): docker container logger used for redirecting log output into a log file
        root_logger (logger): main root loggger
    """

    # Sets processing args.
    processing_args = ['docker', 'logs', '-f', container_name]

    root_logger.debug(f'Starting to redirect the docker container logs for {container_name}')
    root_logger.debug(f'Processing agruments = {processing_args}')

    try:

        # Runs the subprocess and returns output
        output = subprocess.Popen(processing_args,stdout=subprocess.PIPE)

        # Waits as during send pauses. This configuration is required over TextIOWrapper because docker logs can have long breaks between output.
        while output.poll() is None:

            # Writes formated output to log file.
            container_logger.info(output.stdout.readline().decode('utf-8').strip())

        root_logger.debug(f'The docker container logs for {container_name} have stopped outputting. This can happen with the docker container stops running')

    except Exception as err:
        raise ValueError(f'The sub-process failed to run. {err}, Originating error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')


def create_docker_log_threads(docker_container_loggers, root_logger):
    """
    Creates individual threads for each docker container. This allows the docker container logs to process in a separate thread. Required to allow the main program to sleep and active to re-check the threads are still running.

    Args:
        docker_container_loggers (list): a list that contains two entries. The first entry is the docker container name, and the second entry is the logger created for the docker container log output.
        root_logger ([type]): main root loggger

    Returns:
        list: each docker container log thread status is added as a dictionary into a list. The status key returns 'Started' or 'Failed'
            List Example: [[{'Status': 'Started', 'container_name': 'MySoftware1'}], [{'Status': 'Started', 'container_name': 'MySoftware2'}]]

    """

    root_logger.debug('Creating individual threads for each docker container')

    # Holds tread start information
    thread_start_tracker = []

    # Loops through each docker container being monitored.
    for docker_container in docker_container_loggers:

        # Sets easier to read variables from list.
        # Entry Example: ['MySoftware1', <Logger MySoftware1 (Debug)>]
        container_name = docker_container[0]
        container_logger = docker_container[1]

        # Replaces any spaces in the underscores for the thread name
        container_name = container_name.replace(" ", "_")

        # Sets thread name
        thread_name = f'{container_name}_thread'

        root_logger.debug(f'The thread ({thread_name}) is being created for {container_name}')

        # Checks if the start_decryptor_site companion program program is not running for initial startup.
        if thread_name not in str(threading.enumerate()):

            root_logger.info(f'Starting the docker container log capture for {container_name}')

            try:

                # This calls the get_docker_log function and passes the logger details to start monitor the docker container logs.
                # You have to use functools for this to work correctly. Adding the function without functools will cause the function to start before being passed to the start_function_thread.
                start_function_thread(partial(get_docker_log, container_name, container_logger, root_logger), thread_name, False)
                
            except ValueError as err:
                raise ValueError(f'{err}, Error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')
            except Exception as err:
                raise ValueError(f'{err}, Error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')

            # Sleeps 5 seconds to allow startup.
            #time.sleep(1)

            # Validates the start_decryptor_site companion program started.
            if thread_name in str(threading.enumerate()):
                root_logger.info(f'The docker container log capture has started for {container_name}. Thread name = {thread_name}')

                # Adds the thread status into tracker dictionary
                thread_start_tracker.append([{'Status': 'Started', 'container_name': container_name}])

            else:
                root_logger.error(f'Failed to start {thread_name} for {container_name}. The program will continue, but additional troubleshooting will be required. The docker container may not be active.')
                
                # Adds the thread status into tracker dictionary
                thread_start_tracker.append([{'Status': 'Failed', 'container_name': container_name}])

        else:
            root_logger.info(f'The thread ({thread_name}) is still running for {container_name}. No action required')

    return thread_start_tracker


def create_docker_container_loggers(config_yaml_read, central_log_path, max_log_file_size):
    """
    Creates individual docker container loggers for each redirected log docker container.

    Args:
        config_yaml_read (yaml): read in YAML configuration
        central_log_path (str): centralized log output directory for all docker container log redirect files
        max_log_file_size (int): max log file size before log rotation is activated

    Raises:
        ValueError: The YAML software entry section is missing the required keys. Please verify you have set all required keys and try again
        ValueError: The logger creation for the docker container ({container_name}) failed to create

    Returns:
        list: a list of individual docker container loggers. Each line represents an individual docker container. The line will contain the docker container's name and the docker container logger
            Element Example: ['MySoftware1', '<Logger MySoftware2 (Debug)>'']
    """

    # Assigns the docker container name and docker container logger to create a multidimensional list.
    # Placement Example: ['MySoftware1', '<Logger MySoftware2 (Debug)>'']
    docker_container_loggers = []

    # Finds all software monitoring entries in the YAML configuration and loops through each one to pull the configuration settings.
    for key, docker_container in config_yaml_read.get('docker_container').items():
        
        try:

            # Gets software configuration settings from the yaml configuration.
            container_name = docker_container.get('container_name')
            log_name = docker_container.get('log_name')

        except Exception as err:
            raise ValueError(f'The YAML software entry section is missing the required keys. Please verify you have set all required keys and try again, Originating error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')

        # Validates the YAML value.
        # Post-processing values are not required because these are optional settings.
        yaml_value_validation(f'{key} nested key \'container_name\'', container_name, str)
        yaml_value_validation(f'{key} nested key \'log_name\'', log_name, str)

        try: 
            # Gets/Sets the logger for the docker container.
            #
            # These settings are hardcoded and not user programable in the YAML.
            #
            # Sets the name of the logger.
            logger_name = container_name
            # Set the name of the log file.
            container_log_name = log_name
            # Sets the file log level.
            file_log_level = 'INFO'
            # Sets the console log level.
            console_log_level = 'INFO'
            # Sets the log format based on a number option or manual.
            logging_format_option = '%(message)s'
            # Sets handler option.
            logging_handler_option = 2
            # Sets backup copy count
            logging_backup_log_count = 4

            # Calls function to setup logging and create the tracker logger.
            container_logger = create_logger(central_log_path, logger_name, container_log_name, max_log_file_size, file_log_level, console_log_level, logging_backup_log_count, logging_format_option, logging_handler_option)

            # Takes the docker container name/logger and creates a single multidimensional list entry.
            docker_container_loggers.append([container_name, container_logger])

        except Exception as err:
            raise ValueError(f'The logger creation for the docker container ({container_name}) failed to create. {err}, Originating error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')

    return docker_container_loggers


def populate_startup_variables():
    """
    This function populates all hard-coded and yaml-configuration variables into a dictionary that is pulled into the main function.
    YAML entry validation checks are performed within this function. No manual configurations are setup within the program. All user 
    settings are completed in the "docker_log_redirect.yaml" configuration file.

    Raises:
        ValueError: The 'general' key is missing from the YAML file
        ValueError: The 'software' key is missing from the YAML file
        ValueError: The 'email' key is missing from the YAML file
        ValueError: The 'logging' key is missing from the YAML file
        ValueError: NameError
        ValueError: KeyError
        ValueError: General Error

    Returns:
        dict: A dictionary of all startup variables required for the program to run. These startup variables consist of pre-configured and YAML configuration.
    """

    # Initialized an empty dictionary for running variables.
    startup_variables = {}
    # Initialized an empty dictionary for email variables.
    email_settings = {}

    try:

        ##############################################################################
        # Gets the config from the YAML file.
        returned_yaml_read_config = read_yaml_config('docker_log_redirect.yaml')

        # Validates required root keys exist in the YAML configuration.
        if not 'general' in returned_yaml_read_config:
            raise ValueError(f'The \'general\' key is missing from the YAML file, Originating error on line {traceback.extract_stack()[-1].lineno} in <{__name__}>')
        if not 'docker_container' in returned_yaml_read_config:
            raise ValueError(f'The \'software\' key is missing from the YAML file, Originating error on line {traceback.extract_stack()[-1].lineno} in <{__name__}>')
        if not 'email' in returned_yaml_read_config:
            raise ValueError(f'The \'email\' key is missing from the YAML file, Originating error on line {traceback.extract_stack()[-1].lineno} in <{__name__}>')
        if not 'logging' in returned_yaml_read_config:
            raise ValueError(f'The \'logging\' key is missing from the YAML file, Originating error on line {traceback.extract_stack()[-1].lineno} in <{__name__}>')

        # Sets the yaml read configuration to the dictionary.
        startup_variables['imported_yaml_read_config'] = returned_yaml_read_config
        ##############################################################################

        ##############################################################################
        # Gets the central log path directory.
        #
        central_log_path = returned_yaml_read_config.get('general', {}).get('central_log_path')

        # Validates the YAML value.
        yaml_value_validation('central_log_path', central_log_path, str)

        # Sets the program save path to the script directory.
        central_log_path = os.path.abspath(f'{central_log_path}')
        
        # Checks if the central_log_path exists and if not it will be created.
        # This is required because the logs do not save to the root directory.
        if not os.path.exists(central_log_path):
            os.makedirs(central_log_path)

        # Sets the savePath to the startup_variable dictionary.
        startup_variables['central_log_path'] = central_log_path
        ##############################################################################

        ##############################################################################
        # Gets the option to enable or not enable email alerts.
        email_alerts = returned_yaml_read_config.get('general', {}).get('email_alerts')

        # Validates the YAML value.
        yaml_value_validation('email_alerts', email_alerts, bool)

        # Sets the sleep time in seconds to the startup_variable dictionary
        startup_variables['email_alerts'] = email_alerts
        ##############################################################################

        ##############################################################################
        # Gets the option to enable or not enable program error email alerts.
        #
        alert_program_errors = returned_yaml_read_config.get('general', {}).get('alert_program_errors')

        # Validates the YAML value.
        yaml_value_validation('alert_program_errors', alert_program_errors, bool)

        # Sets the sleep time in seconds to the startup_variable dictionary
        startup_variables['alert_program_errors'] = alert_program_errors
        ##############################################################################

        ##############################################################################
        # Gets the max log size.
        #
        # Calling function to set the max log size in bytes.
        # Default 1000000 Byltes (1 Megabyte)
        max_log_file_size = returned_yaml_read_config.get('logging', {}).get('max_log_file_size')

        # Validates the YAML value.
        yaml_value_validation('max_log_file_size', max_log_file_size, int)
        ##############################################################################

        ##############################################################################
        # Gets/Sets the root logger.
        #
        # Sets the name of the logger.
        logger_name = __name__
        # Set the name of the log file.
        log_name = 'docker_log_redirect.log'
        # Sets the file log level.
        file_log_level = returned_yaml_read_config.get('logging', {}).get('file_log_level')
        # Sets the console log level.
        console_log_level = returned_yaml_read_config.get('logging', {}).get('console_log_level')
        # Sets the log format based on a number option or manual.
        logging_format_option = returned_yaml_read_config.get('logging', {}).get('logging_format_option')
        # Sets handler option.
        logging_handler_option = returned_yaml_read_config.get('logging', {}).get('logging_handler_option')
        # Sets the backup count.
        logging_backup_log_count = returned_yaml_read_config.get('logging', {}).get('logging_backup_log_count')

        # Validates the YAML value.
        yaml_value_validation('file_log_level', file_log_level, str)
        yaml_value_validation('console_log_level', console_log_level, str)
        yaml_value_validation('logging_handler_option', logging_handler_option, int)
        yaml_value_validation('logging_backup_log_count', logging_backup_log_count, int)

        # Sets LoggingFormatOption entry type based on input.
        # Checks if user entered a custom format or selected a pre-configured option.
        if '%' in f'{logging_format_option}':
            # Removes single quotes from logging format if they exist.
            logging_format_option = logging_format_option.replace("'", "")
        else:

            # Validates the YAML value.
            yaml_value_validation('logging_format_option', logging_format_option, int)

            # Converts string to int because the user selected a pre-configured option.
            logging_format_option = int(logging_format_option)
            
        # Calls function to setup logging and create the root logger.
        root_logger = create_logger(central_log_path, logger_name, log_name, max_log_file_size, file_log_level, console_log_level, logging_backup_log_count, logging_format_option, logging_handler_option)
        
        # Sets the tracker_logger to the startup_variable dictionary.
        startup_variables['root_logger'] = root_logger
        ##############################################################################

        ##############################################################################
        # Gets/Sets the docker container logger per YAML entry by calling the function using the user-selected docker container name and docker container file name.
        # Each docker container will have its own logger for output.
        #
        # Return Example: [['MySoftware1', <Logger MySoftware1 (Debug)>], ['MySoftware2', <Logger MySoftware2 (Debug)>]]
        docker_container_loggers = create_docker_container_loggers(returned_yaml_read_config, central_log_path, max_log_file_size)
        ##############################################################################

        ##############################################################################
        # Sets the monitored software settings to the startup_variable dictionary
        startup_variables['docker_container_loggers'] = docker_container_loggers
        ##############################################################################

        ##############################################################################
        # Sets email values.
        smtp = returned_yaml_read_config.get('email', {}).get('smtp')
        authentication_required = returned_yaml_read_config.get('email', {}).get('authentication_required')
        use_tls = returned_yaml_read_config.get('email', {}).get('use_tls')
        username = returned_yaml_read_config.get('email', {}).get('username')
        password = returned_yaml_read_config.get('email', {}).get('password')
        from_email = returned_yaml_read_config.get('email', {}).get('from_email')
        to_email = returned_yaml_read_config.get('email', {}).get('to_email')
        #Manually disabling encryption because sensitive information will not be emailed. Removing the option from YAML.
        send_message_encrypted = False

        # Validates the YAML value.
        yaml_value_validation('smtp', smtp, str)
        yaml_value_validation('authentication_required', authentication_required, bool)
        yaml_value_validation('use_tls', use_tls, bool)
        yaml_value_validation('username', username, str)
        yaml_value_validation('password', password, str)
        yaml_value_validation('from_email', from_email, str)
        yaml_value_validation('to_email', to_email, str)


        # Adds the email_settings into a dictionary.
        email_settings['smtp'] = smtp
        email_settings['authentication_required'] = authentication_required
        email_settings['use_tls'] = use_tls
        email_settings['username'] = username
        email_settings['password'] = password
        email_settings['from_email'] = from_email
        email_settings['to_email'] = to_email
        email_settings['send_message_encrypted'] = send_message_encrypted

        # Sets email dictionary settings to the startup_variable dictionary.
        startup_variables['email_settings'] = email_settings
        ##############################################################################

        # Returns the dictionary with all the startup variables.
        return (startup_variables)

    except NameError as err:
        raise ValueError(f'NameError: {err}, Error on line{traceback.extract_stack()[-1].lineno} in <{__name__}>')

    except KeyError as err:
        raise ValueError(f'KeyError: {err}, Error on line{traceback.extract_stack()[-1].lineno} in <{__name__}>')

    except Exception as err:
        raise ValueError(f'{err}, Error on line{traceback.extract_stack()[-1].lineno} in <{__name__}>')


def main():
    """This function is main program function that controls all the sub-function calls. A loop set to allow this program to run all time and process based on a sleep variable."""
    
    # Calls function to pull in the startup variables.
    startup_variables = populate_startup_variables()

    # Sets top-level main variables based on the dictionary of presets.
    # Note: Using [] will give KeyError and using get() will return None.
    central_log_path = startup_variables.get('central_log_path')
    email_alerts = startup_variables.get('email_alerts')
    alert_program_errors = startup_variables.get('alert_program_errors')
    root_logger = startup_variables.get('root_logger')
    docker_container_loggers = startup_variables.get('docker_container_loggers')
    email_settings = startup_variables.get('email_settings')

    root_logger.info('######################################################################')
    root_logger.info('                   Docker Log Redirect - New Loop                     ')
    root_logger.info('######################################################################')

    try:

        # Calls function to monitor the docker logs.
        # Example REturn: [[{'Status': 'Started', 'container_name': 'MySoftware1'}], [{'Status': 'Started', 'container_name': 'MySoftware2'}]]
        thread_status = create_docker_log_threads(docker_container_loggers, root_logger)

        # Sets count on total entries found
        total_thread_status_entries = len(thread_status)

        # Loops through each dictionary in the thread_status list.
        for thread_status_of_dictionary in thread_status:
            
            # Loops through each item in the dictionary entry.
            for index, value in enumerate(thread_status_of_dictionary):
                
                # Sets the status value to a variable. This is done to decrease the code complexity.
                status =value.get('Status')
                # Sets the container name value to a variable. This is done to decrease the code complexity.
                container_name = value.get('container_name')

                # Checks if email notifications are enabled
                if email_alerts:

                    root_logger.info(f'Sending email. Entry {index + 1} of {total_thread_status_entries }')

                    # Calls function to send the email.
                    # Calling Example: send_email(<Dictionary: email settings>, <Subject>, <Issue Message To Send>, <configured logger>)
                    send_email(email_settings, f'Docker Log Redirect Event for {container_name}. Status = {status}', f'A docker redirect event has occured. Status of the docker log redirect = {status}', root_logger)  
                
                else:
                    
                    root_logger.info('Email alerting is disabled. The found log event is not be sent')

    except ValueError as err:

        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|Error|{err}, Error on line {format(sys.exc_info()[-1].tb_lineno)} in <{__name__}>')

        ###########################################################
        # Currently the program is exiting on any discovered error. 
        ###########################################################

        # System exit print output for general setup
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|Error|{err}')
        print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|Info|See log for more details. You may need to enable debugging for more information.')

        root_logger.error(f'{err}')
        
        # Checking if the user chooses not to send program errors to email.
        if alert_program_errors == True and email_alerts == True:

            root_logger.error('Sending email notification')
            
            try:
                
                # Calls function to send the email.
                # Calling Example: send_email(<Dictionary: email settings>, <Subject>, <Issue Message To Send>, <configured logger>)
                send_email(email_settings, "Docker Log Redirect Program Issue Occured", f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|Error|Exception Thrown|{err}', root_logger)

            except Exception as err:
                root_logger.error(f'{err}')

        elif alert_program_errors == False:
            root_logger.debug(f'The user chooses not to send program errors to email')
        else:
            root_logger.error('The user did not choose an option on sending program errors to email. Continuing to exit')

        root_logger.error('Exiting because of the exception error....')

        exit()

    root_logger.info('The main program will sleep for 1 hour and validate the docker log redirect threads are still running.')


# Checks that this is the main program initiates the classes to start the functions.
if __name__ == "__main__":

    # Prints out at the start of the program.
    print('# ' + '=' * 85)
    print('Author: ' + __author__)
    print('Copyright: ' + __copyright__)
    print('Credits: ' + ', '.join(__credits__))
    print('License: ' + __license__)
    print('Version: ' + __version__)
    print('Maintainer: ' + __maintainer__)
    print('Status: ' + __status__)
    print('# ' + '=' * 85)

    # Loops to keep the main program active. 
    # The YAML configuration file will contain a sleep setting within the main function.
    while True:

        # Calls main function.
        main()
        
        # 1-hour delay sleep. Each hour the program will check that the threads are still running and the docker container logs are redirecting.
        time.sleep(3600)