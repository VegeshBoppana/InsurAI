import os
import resend
import base64
from fpdf import FPDF
from dotenv import load_dotenv
load_dotenv()



# ---------------------------
# PDF Generator
# ---------------------------
def generate_policy_pdf(user_name, policy_name, premium, coverage, benefits, insurance_type, filename="policy.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    pdf.cell(200, 10, "InsurAI Insurance Policy Document", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Policy Holder: {user_name}", ln=True)
    pdf.cell(200, 10, f"Policy Type: {insurance_type.capitalize()}", ln=True)
    pdf.cell(200, 10, f"Policy Name: {policy_name}", ln=True)
    pdf.cell(200, 10, f"Premium: INR {premium}/year", ln=True)
    pdf.cell(200, 10, f"Coverage: INR {coverage}", ln=True)
    pdf.multi_cell(200, 10, f"Benefits: {benefits}", align="L")

    pdf.ln(10)
    pdf.cell(200, 10, "This is a system-generated insurance policy.", ln=True, align="C")

    pdf.output(filename)
    return filename


# ---------------------------
# Email Sender (Resend API)
# ---------------------------
def send_policy_email(to_email, subject, body, attachment_path):
    resend.api_key = os.getenv("RESEND_API_KEY")

    with open(attachment_path, "rb") as f:
        file_data = f.read()
        encoded_file = base64.b64encode(file_data).decode("utf-8")  # ✅ Encode to Base64

    params = {
        "from": os.getenv("EMAIL_SENDER"),
        "to": [to_email],
        "subject": subject,
        "html": body.replace("\n", "<br>"),
        "attachments": [
            {
                "filename": os.path.basename(attachment_path),
                "content": encoded_file,               # ✅ Base64 string
                "type": "application/pdf"              # ✅ MIME type
            }
        ]
    }

    email = resend.Emails.send(params)
    print(f"📧 Email sent via Resend to {to_email}, ID={email['id']}")
