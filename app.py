import asyncio
from flask import Flask, make_response, render_template, jsonify, request, redirect, url_for, flash
import threading
import pdfkit
from datetime import datetime
import logging
import os
import json
import pandas as pd
from werkzeug.utils import secure_filename
from config import config
from website_monitor.monitor import periodic_monitoring, websites

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Configure logging
log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        *([logging.FileHandler(config.LOG_FILE)] if config.LOG_FILE else [])
    ]
)
logger = logging.getLogger(__name__)

# Thread lock for safe access to websites data
websites_lock = threading.Lock()

# Start the async monitoring in a separate thread
monitor_thread = threading.Thread(target=periodic_monitoring, daemon=True)
monitor_thread.start()


def get_sorted_websites():
    """Get a thread-safe copy of websites data sorted by status"""
    with websites_lock:
        return dict(sorted(websites.items(), key=lambda item: (
            0 if item[1]['status'] == 'DOWN' else
            1 if item[1]['status'] == 'SLOW' else 2
        )))


@app.route("/")
def index():
    try:
        websites_list = get_sorted_websites()
        return render_template("index.html",
                               websites=websites_list,
                               last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return f"An error occurred: {e}", 500


@app.route("/api/status")
def api_status():
    """API endpoint for real-time status updates"""
    try:
        websites_list = get_sorted_websites()
        return jsonify({
            'websites': websites_list,
            'last_updated': datetime.now().isoformat(),
            'total_sites': len(websites_list),
            'down_sites': sum(1 for site in websites_list.values() if site['status'] == 'DOWN')
        })
    except Exception as e:
        logger.error(f"Error in API status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/export_pdf")
def export_pdf():
    try:
        websites_list = get_sorted_websites()
        html = render_template("index.html",
                               websites=websites_list,
                               last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Configure pdfkit options with wkhtmltopdf path
        pdf_config = pdfkit.configuration(wkhtmltopdf=config.WKHTMLTOPDF_PATH)

        options = {
            'page-size': 'A4',
            'margin-top': '0.5cm',
            'margin-right': '0.5cm',
            'margin-bottom': '0.5cm',
            'margin-left': '0.5cm',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
            'print-media-type': None
        }

        # Create a PDF from the rendered HTML
        pdf = pdfkit.from_string(
            html, False, options=options, configuration=pdf_config)

        # Create a response object with timestamp in filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'website_status_{timestamp}.pdf'

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
    except Exception as e:
        logger.error(f"Error in PDF export: {e}")
        return f"PDF generation failed: {e}", 500


@app.route("/manage")
def manage_websites():
    """Website management page"""
    try:
        websites_list = get_sorted_websites()
        return render_template("manage.html", websites=websites_list)
    except Exception as e:
        logger.error(f"Error in manage route: {e}")
        return f"An error occurred: {e}", 500


@app.route("/add_website", methods=["POST"])
def add_website():
    """Add a single website manually"""
    try:
        url = request.form.get('url', '').strip()
        if not url:
            flash('Please enter a valid URL', 'error')
            return redirect(url_for('manage_websites'))

        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Add to websites dictionary with thread safety
        with websites_lock:
            if url not in websites:
                websites[url] = {
                    'status': 'UNKNOWN',
                    'ip': None,
                    'status_code': None,
                    'response_time': None,
                    'error_count': 0,
                    'last_check': None,
                    'screenshot': None
                }
                flash(f'Website {url} added successfully!', 'success')
                logger.info(f"Added website: {url}")
            else:
                flash(f'Website {url} already exists!', 'warning')

        return redirect(url_for('manage_websites'))
    except Exception as e:
        logger.error(f"Error adding website: {e}")
        flash('Failed to add website', 'error')
        return redirect(url_for('manage_websites'))


@app.route("/remove_website", methods=["POST"])
def remove_website():
    """Remove a website"""
    try:
        url = request.form.get('url', '').strip()
        if not url:
            flash('Invalid URL provided', 'error')
            return redirect(url_for('manage_websites'))

        # Remove from websites dictionary with thread safety
        with websites_lock:
            if url in websites:
                del websites[url]
                flash(f'Website {url} removed successfully!', 'success')
                logger.info(f"Removed website: {url}")
            else:
                flash(f'Website {url} not found!', 'error')

        return redirect(url_for('manage_websites'))
    except Exception as e:
        logger.error(f"Error removing website: {e}")
        flash('Failed to remove website', 'error')
        return redirect(url_for('manage_websites'))


@app.route("/upload_websites", methods=["POST"])
def upload_websites():
    """Upload websites from a file (Excel, CSV, or TXT)"""
    try:
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('manage_websites'))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('manage_websites'))

        if file:
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit(
                '.', 1)[1].lower() if '.' in filename else ''

            if file_ext not in ['xlsx', 'xls', 'csv', 'txt']:
                flash(
                    'Invalid file format. Please upload Excel, CSV, or TXT files only.', 'error')
                return redirect(url_for('manage_websites'))

            # Save uploaded file temporarily
            upload_path = os.path.join('temp_uploads', filename)
            os.makedirs('temp_uploads', exist_ok=True)
            file.save(upload_path)

            try:
                websites_to_add = []

                if file_ext in ['xlsx', 'xls']:
                    # Read Excel file
                    df = pd.read_excel(upload_path)
                    # Look for URL column (try different possible column names)
                    url_column = None
                    for col in df.columns:
                        if any(term in col.lower() for term in ['url', 'website', 'domain', 'site']):
                            url_column = col
                            break

                    if url_column is None and len(df.columns) > 0:
                        # Use first column if no URL column found
                        url_column = df.columns[0]

                    if url_column:
                        websites_to_add = df[url_column].dropna().astype(
                            str).tolist()

                elif file_ext == 'csv':
                    # Read CSV file
                    df = pd.read_csv(upload_path)
                    # Look for URL column
                    url_column = None
                    for col in df.columns:
                        if any(term in col.lower() for term in ['url', 'website', 'domain', 'site']):
                            url_column = col
                            break

                    if url_column is None and len(df.columns) > 0:
                        # Use first column if no URL column found
                        url_column = df.columns[0]

                    if url_column:
                        websites_to_add = df[url_column].dropna().astype(
                            str).tolist()

                elif file_ext == 'txt':
                    # Read text file (one URL per line)
                    with open(upload_path, 'r', encoding='utf-8') as f:
                        websites_to_add = [line.strip()
                                           for line in f.readlines() if line.strip()]

                # Clean and add websites
                added_count = 0
                duplicate_count = 0

                with websites_lock:
                    for url in websites_to_add:
                        url = url.strip()
                        if not url:
                            continue

                        # Add http:// if no protocol specified
                        if not url.startswith(('http://', 'https://')):
                            url = 'https://' + url

                        if url not in websites:
                            websites[url] = {
                                'status': 'UNKNOWN',
                                'ip': None,
                                'status_code': None,
                                'response_time': None,
                                'error_count': 0,
                                'last_check': None,
                                'screenshot': None
                            }
                            added_count += 1
                        else:
                            duplicate_count += 1

                # Clean up uploaded file
                os.remove(upload_path)

                if added_count > 0:
                    flash(
                        f'Successfully added {added_count} websites!', 'success')
                    logger.info(
                        f"Added {added_count} websites from file upload")
                if duplicate_count > 0:
                    flash(
                        f'{duplicate_count} websites were already in the list', 'warning')

                if added_count == 0 and duplicate_count == 0:
                    flash('No valid websites found in the file', 'error')

            except Exception as e:
                # Clean up uploaded file on error
                if os.path.exists(upload_path):
                    os.remove(upload_path)
                logger.error(f"Error processing uploaded file: {e}")
                flash('Error processing uploaded file', 'error')

        return redirect(url_for('manage_websites'))
    except Exception as e:
        logger.error(f"Error in file upload: {e}")
        flash('Failed to upload file', 'error')
        return redirect(url_for('manage_websites'))


@app.route("/check_website/<path:url>", methods=["POST"])
def check_website_now(url):
    """Manually trigger a check for a specific website"""
    try:
        from website_monitor.monitor import check_website

        # Decode the URL
        import urllib.parse
        url = urllib.parse.unquote(url)

        # Check if website exists in our list
        with websites_lock:
            if url not in websites:
                return jsonify({'error': 'Website not found'}), 404

        # Trigger the check
        success = check_website(url)

        # Get updated status
        with websites_lock:
            website_data = websites.get(url, {})

        return jsonify({
            'success': True,
            'url': url,
            'status': website_data.get('status', 'UNKNOWN'),
            'status_code': website_data.get('status_code'),
            'response_time': website_data.get('response_time'),
            'ip': website_data.get('ip'),
            'last_check': website_data.get('last_check'),
            'message': 'Website checked successfully'
        })

    except Exception as e:
        logger.error(f"Error checking website {url}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/check_all_websites", methods=["POST"])
def check_all_websites():
    """Manually trigger a check for all websites"""
    try:
        from website_monitor.monitor import check_websites

        # Trigger checks for all websites
        check_websites()

        return jsonify({
            'success': True,
            'message': 'All websites check initiated'
        })

    except Exception as e:
        logger.error(f"Error checking all websites: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/export_websites")
def export_websites():
    """Export current websites list to Excel"""
    try:
        websites_list = get_sorted_websites()

        # Create DataFrame
        data = []
        for url, info in websites_list.items():
            data.append({
                'URL': url,
                'Status': info.get('status', 'UNKNOWN'),
                'IP Address': info.get('ip', ''),
                'Status Code': info.get('status_code', ''),
                'Response Time': info.get('response_time', ''),
                'Error Count': info.get('error_count', 0),
                'Last Check': info.get('last_check', '')
            })

        df = pd.DataFrame(data)

        # Create Excel file in memory
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Websites', index=False)

        output.seek(0)

        # Create response
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'websites_list_{timestamp}.xlsx'

        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        return response
    except Exception as e:
        logger.error(f"Error exporting websites: {e}")
        flash('Failed to export websites list', 'error')
        return redirect(url_for('manage_websites'))


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500


if __name__ == "__main__":
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
