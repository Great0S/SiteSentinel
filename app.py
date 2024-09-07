import asyncio
from flask import Flask, make_response, render_template
import threading
from weasyprint import CSS, HTML
from website_monitor.monitor import periodic_monitoring, websites

app = Flask(__name__)

# Start the async monitoring in a separate thread
monitor_thread = threading.Thread(target=periodic_monitoring, daemon=True)
monitor_thread.start()
websites_list = dict(sorted(websites.items(), key=lambda item: item[1]['status'], reverse=False))

@app.route("/")
def index():
    try:        
        return render_template("index.html", websites=websites_list)
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route("/export_pdf")
def export_pdf():
    try:
        html = render_template("index.html", websites=websites_list)
        
        # Create a PDF from the rendered HTML
        css = CSS(string='@page { size: A4; margin: 0.5cm; }')
        pdf = HTML(string=html).write_pdf(stylesheets=[css])
        
        # Create a response object
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=website_status.pdf'
        return response
    except Exception as e:
        return f"An error occurred: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
