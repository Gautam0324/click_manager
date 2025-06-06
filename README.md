# click_manager


Flask URL and Device Management Application
Overview
This is a Flask-based web application designed to manage URLs and devices, interacting with a MySQL database to store and manipulate data. The application allows users to:

Add, update, and toggle the selection of URLs and devices.
Track URL clicks with attributes like target clicks, unique/repeated percentages, and campaign names.
Manage devices with attributes like ADB ID, asset number, and state.
Start and stop a background script (main_script.py) via API endpoints.
Log application activities for debugging and monitoring.

The application uses a MySQL connection pool for efficient database interactions and includes logging for error tracking and debugging.
Prerequisites
To run this application, ensure you have the following installed:

Python 3.12 or higher
MySQL Server (accessible at 82.180.144.17 or configured to your environment)
Required Python packages (listed in requirements.txt):
flask
mysql-connector-python



Installation

Clone the Repository:
git clone <repository_url>
cd <repository_directory>


Set Up a Virtual Environment (optional but recommended):
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt


Configure the Database:

Ensure the MySQL database IP_satish_sir is set up and accessible.
Update the DB_CONFIG dictionary in the Flask application (app.py) with your database credentials if different:DB_CONFIG = {
    'host': 'your_host',
    'user': 'your_user',
    'password': 'your_password',
    'database': 'your_database',
    'pool_name': 'mypool',
    'pool_size': 5
}




Set Up the Database Schema:

The application automatically adds necessary columns (is_selected, campaign_name, asset_no, state) to the url_clicks and device tables if they don't exist.
Ensure the url_clicks and device tables are created with the following structure:CREATE TABLE url_clicks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(255) NOT NULL,
    target_clicks INT NOT NULL,
    unique_percent FLOAT NOT NULL,
    repeated_percent FLOAT NOT NULL,
    campaign_name VARCHAR(255),
    is_selected BOOLEAN DEFAULT 0
);

CREATE TABLE device (
    id INT AUTO_INCREMENT PRIMARY KEY,
    adb_id VARCHAR(100) NOT NULL,
    asset_no VARCHAR(100),
    state VARCHAR(100),
    is_selected BOOLEAN DEFAULT 0
);




Prepare the Script:

Ensure the main_script.py file exists in the same directory as the Flask application. This script is executed via the /run-script endpoint.
Update the Python path in the run_script function if necessary:script_process = subprocess.Popen([
    r'C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe',
    script_path
])





Running the Application

Start the Flask Application:
python app.py

The application will run on http://0.0.0.0:5000 in debug mode.

Access the Application:

Open a web browser and navigate to http://localhost:5000 to access the main interface.
The interface allows you to add, update, and toggle the selection of URLs and devices.



Features

URL Management:
Add new URLs with target clicks, unique/repeated percentages, and optional campaign names.
Update existing URLs.
Toggle URL selection status for tracking active URLs.


Device Management:
Add new devices with ADB ID, asset number, and state.
Update existing devices.
Toggle device selection status for tracking active devices.


Script Execution:
Start the main_script.py script via the /run-script endpoint.
Stop the running script via the /stop-script endpoint.


Database Integration:
Uses a MySQL connection pool for efficient database access.
Automatically ensures required table columns exist.


Logging:
Logs application activities, errors, and database interactions to app.log.



API Endpoints

GET/POST /:
Displays the main interface and handles form submissions for adding URLs and devices.


POST /toggle_device_selection/<id>:
Toggles the selection status of a device by ID.


POST /toggle_url_selection/<id>:
Toggles the selection status of a URL by ID.


POST /update_url/<id>:
Updates the details of a URL by ID.


POST /update_device/<id>:
Updates the details of a device by ID.


GET /used_devices:
Returns a JSON list of selected or active devices.


POST /run-script:
Starts the main_script.py script if not already running.


POST /stop-script:
Stops the running main_script.py script.



Logging

Logs are stored in app.log in the application directory.
Logs include timestamps, log levels (INFO, WARNING, ERROR), and messages for debugging and monitoring.

Troubleshooting

Database Connection Issues:
Verify the MySQL server is running and accessible at the specified host (82.180.144.17).
Check the database credentials in DB_CONFIG.


Script Execution Issues:
Ensure main_script.py exists in the correct directory.
Verify the Python path in the run_script function matches your Python installation.


Form Validation Errors:
Ensure all required fields (URL, target, unique/repeated percentages for URLs; ADB ID, asset number, state for devices) are provided in forms.


Port Conflicts:
If port 5000 is in use, change the port in app.run(port=5000).



Contributing
Contributions are welcome! Please submit a pull request or open an issue for bugs, features, or improvements.
License
This project is licensed under the MIT License. See the LICENSE file for details.
