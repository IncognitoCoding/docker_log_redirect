# docker_log_redirect
 
# Overview:
docker_log_redirect offers you the ability to quickly set up and centralize all of your logs into one central directory. All configuration is set up through a simple to use YAML configuration file, and you can add as many docker containers log redirect entries as you would like to centralize. No modifications to your docker containers or configuration are required.

If you would like to alert on these centralized docker logs, check out [software_log_monitor] (https://github.com/IncognitoCoding/software_log_monitor). 

## Program Highlights:
* Dynamically add as many docker containers as you would like to redirect.
* Each docker container redirect entry runs under its dedicated thread.
* Email supports standard port 25 or TLS.
* Email notification when docker redirect thread starts or fails.
* Customizable program log output and debug options.
* The YAML file allows updating on the fly, and each loop will use the updated YAML configuration.

## Setup Recommendations & Setup Hints:
Each docker container is considered a separate docker container entry in the program. Each docker container entry must contain the required YAML keys. Copy the previous sample section when adding a new docker container entry and change the last number.

The sample file is designed to show you two different docker container examples to show what options you can use.

# Program Prerequisites:
Use the requirements.txt file to make sure you have all the required prerequisites. This program will use an additional package called ictoolkit created by IncognitoCoding for most general function calls. Future programs will utilize the similar ictoolkit package. Feel free to use this package for your Python programming.

## How to Use:
The sample YAML configuration file has plenty of notes to help explain the setup process. The steps below will explain what needs to be done to get the program running.

    Step 1: For the program to recognize the YAML file, you must copy the sample_docker_log_redirect.yaml file and rename it to docker_log_redirect.yaml 
    Step 2: Update the YAML file with your configuration.
    Step 3: Run the program to make sure your settings are entered correctly. 
    Step 4: Depending on your operating system (Linux Ubuntu or Windows), you can set up the program to run automatically, which is recommended. Other Linux versions will work but are not explained below. 
       Step 4.1 (Optional - Windows): Setup a scheduled task to run the program on startup.
                Create a service account and a new scheduled task using these settings. 
                    - Run weather user is logged on or not
                    - Run with highest privileges
                    - Run hidden
                    - Set trigger time. Maybe daily around midnight
                    - Set action to start program
                    - Program/Script: python
                    - Arguments: "C:\<path to the program>\docker_log_redirect\docker_log_redirect.py"
       Step 4.2 (Optional - Linux Ubuntu): Set up a service to run the program.
            Step 4.2.1:  Create a new service file.
                Run: cd /lib/systemd/system
                Run: sudo nano docker_log_redirect.service
                    Note: The service account needs to have docker socket access. The root user is added below as an example.
                    Paste:
                        Description=docker_log_redirect
                        After=multi-user.target
                        After=network.target

                        [Service]
                        Type=simple
                        User=root
                        WorkingDirectory=/<path to program>/docker_log_redirect
                        ExecStart=/usr/bin/python3  /<path to program>/docker_log_redirect/docker_log_redirect.py                                                         
                        Restart=always

                        [Install]
                        WantedBy=multi-user.target
            Step 4.2.2:  Create a new service file.
                Run: sudo systemctl daemon-reload
            Step 4.2.3: Enable the new service.
                sudo systemctl enable docker_log_redirect.service
            Step 4.2.4: Start the new service.
                sudo systemctl start docker_log_redirect.service
            Step 4.2.5: Check the status of the new service.
                sudo systemctl status docker_log_redirect.service
    Step 5: Verify the program is running as a service or scheduled task. 
    Step 6: Once verified, you should set the logging handler to option 2 and the file's log level to INFO. This will cut down on disk space.
## Troubleshooting:
The YAML file offers DEBUG options to troubleshoot any issues you encounter. Please report any bugs.
