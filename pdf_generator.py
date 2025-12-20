import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

def generate_pdf(articles, output_filename="morning_dossier.pdf"):
    print("Generating PDF...")
    
    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('magazine.html')
    
    # Current date
    date_str = datetime.now().strftime("%B %d, %Y")
    
    # Render HTML
    html_content = template.render(
        articles=articles,
        date=date_str
    )
    
    # Save debug HTML
    with open("debug.html", "w") as f:
        f.write(html_content)
    
    # Generate PDF
    # base_url is needed for relative paths (images) to resolve correctly
    # We set it to the current working directory
    try:
        HTML(string=html_content, base_url=os.getcwd()).write_pdf(output_filename)
        print(f"PDF generated successfully: {output_filename}")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error generating PDF: {e}")
        return False

