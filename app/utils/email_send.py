# Email sending utilities using SendGrid API
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: str = None,
    from_name: str = "FDC Fantatorneo",
) -> dict:
    """
    Send an email via SendGrid API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML body content
        from_email: Sender email (defaults to env SENDER_EMAIL)
        from_name: Sender display name
    
    Returns:
        dict with status_code and response from SendGrid API
    
    Raises:
        ValueError: if SENDGRID_API_KEY or SENDER_EMAIL not configured
    """
    # Get API key from environment
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        raise ValueError("SENDGRID_API_KEY environment variable not set")
    
    # Get default sender if not provided
    if not from_email:
        from_email = os.getenv("SENDER_EMAIL")
        if not from_email:
            raise ValueError("SENDER_EMAIL environment variable not set or not provided")
    
    # Create and send mail object
    message = Mail(
        from_email=Email(from_email, from_name),
        to_emails=To(to_email),
        subject=subject,
        html_content=html_content,
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return {
            "status_code": response.status_code,
            "body": response.body,
            "headers": response.headers,
        }
    except Exception as e:
        raise RuntimeError(f"Failed to send email via SendGrid: {str(e)}")


# Optional: test function for local testing (requires env vars set)
if __name__ == "__main__":
    result = send_email(
        to_email="test@example.com",
        subject="Test Email from FDC Fantatorneo",
        html_content="<strong>Test email successful!</strong>",
    )
    print(f"Email sent with status code: {result['status_code']}")
