# Site Sentinel - Website Monitoring Dashboard

The **Site Sentinel** is a Python-based application that tracks the availability and errors of a list of websites. It periodically checks each website and alerts users via email if any of them go down. The dashboard displays the website status, error count, and IP address in real time, and also includes a feature to export the status to a PDF.

## Features

- Daily monitoring of websites for availability and errors.
- Real-time dashboard with website status, error count, and IP address.
- Email alerts when a website goes down for a configurable number of consecutive checks.
- Export website status to PDF.
- Retry logic and error threshold management.

## Technologies Used

- **Python**: Core programming language for website checks and backend logic.
- **Flask**: Web framework for the dashboard UI.
- **smtplib**: Python library for sending email alerts.
- **socket**: For resolving website IP addresses.
- **Jinja2**: Templating engine for rendering the HTML dashboard.
- **WeasyPrint**: For exporting the dashboard to PDF.
- **Pandas**: For reading website data from Excel files.

## Prerequisites

- Python 3.x
- Flask
- WeasyPrint
- Pandas
- An SMTP server for email alerts

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Great0S/SiteSentinel.git
    cd SiteSentinel
    ```

2. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Modify the following environment variables in the script for email functionality:
    - `EMAIL_SENDER`: Your email address for sending alerts.
    - `EMAIL_PASSWORD`: Your email password.
    - `EMAIL_RECEIVER`: The email address where alerts will be received.
    - `ERROR_THRESHOLD`: Number of consecutive failed checks to trigger an email alert.

4. Add your list of websites in the `domainler.xlsx` file (under the "Domain" column).

## Usage

1. **Run the application:**
    ```bash
    python app.py
    ```

2. **Access the Dashboard:**
    Open your browser and navigate to:
    ```
    http://localhost:5000/
    ```

3. **Check Website Status:**
    The dashboard will display each website's:
    - Domain name
    - IP address
    - Status (Up/Down/Error)
    - Error count

4. **Export to PDF:**
    Click the "Export to PDF" button on the dashboard to download the current status report as a PDF file.

## Email Alerts

The app sends an email alert if a website is down for a number of consecutive checks defined by the `ERROR_THRESHOLD`. Ensure you have configured your SMTP server and login details correctly.

### Example Email Alert
Subject: Website Down Alert: https://example.com

ALERT: The website https://example.com is down for 3 consecutive checks.


## Contributing

Feel free to fork the project and submit pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


