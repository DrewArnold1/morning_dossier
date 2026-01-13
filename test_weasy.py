from weasyprint import HTML
import sys

try:
    print("Attempting to generate test PDF...")
    HTML(string="<h1>Hello World</h1>").write_pdf("test.pdf")
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()


