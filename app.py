from flask import Flask, make_response, render_template
import threading

from weasyprint import CSS, HTML
from website_monitor.monitor import websites, start_monitoring

app = Flask(__name__)

# Start the monitoring in a separate thread so it runs in the background
monitor_thread = threading.Thread(target=start_monitoring)
monitor_thread.daemon = True
monitor_thread.start()

@app.route("/")
def index():
    # Sort websites by status ('Up', 'Error', 'Down')
    sorted_websites = dict(sorted(websites.items(), key=lambda item: item[1]['status'], reverse=False))
    return render_template("index.html", websites=sorted_websites)

@app.route("/export_pdf")
def export_pdf():
    # Render the HTML template
    html = render_template("index.html", websites=websites)
    
    # Create a PDF from the rendered HTML
    css = CSS(string='@page { size: A4; margin: 0.5cm }, @button { width: 20px;}')
    pdf = HTML(string=html).write_pdf(stylesheets=[css])
    
    # Create a response object
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=website_status.pdf'
    return response

if __name__ == "__main__":
    app.run(debug=True)
