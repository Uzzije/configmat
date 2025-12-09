import brevo_python
from brevo_python.rest import ApiException
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_invitation_email(email, invite_link, inviter_name=None):
    """
    Send an invitation email using Brevo.
    """
    if not settings.BREVO_API_KEY:
        logger.warning("BREVO_API_KEY not set. Skipping email sending.")
        return False

    configuration = brevo_python.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = brevo_python.TransactionalEmailsApi(brevo_python.ApiClient(configuration))
    
    subject = "You've been invited to ConfigMat"
    html_content = f"""
    <html>
    <body>
        <h1>Welcome to ConfigMat</h1>
        <p>Hello,</p>
        <p>{inviter_name or 'Someone'} has invited you to join their team on ConfigMat.</p>
        <p>Click the link below to accept the invitation:</p>
        <p><a href="{invite_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Accept Invitation</a></p>
        <p>Or copy this link: {invite_link}</p>
        <p>If you didn't expect this invitation, you can ignore this email.</p>
    </body>
    </html>
    """
    
    sender = {"name": "ConfigMat", "email": "no-reply@configmat.com"}
    to = [{"email": email}]
    
    send_smtp_email = brevo_python.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent to {email}: {api_response}")
        return True
    except ApiException as e:
        logger.error(f"Exception when calling TransactionalEmailsApi->send_transac_email: {e}")
        return False
