# backend/app/utils/email_service.py
"""
Email service for sending notifications and password reset emails
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handle all email sending operations"""
    
    def __init__(self):
        # Email configuration
        self.smtp_server = "smtp.gmail.com"  # Change for other providers
        self.smtp_port = 587
        self.sender_email = settings.EMAIL_HOST_USER
        self.sender_password = settings.EMAIL_HOST_PASSWORD
        self.sender_name = "Smart Job Finder"
        # FIXED: Use environment variable for frontend URL with correct path
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5500/smartJobFinder/frontend')
    
    def _create_connection(self):
        """Create SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            if self.sender_email and self.sender_password:
                server.login(self.sender_email, self.sender_password)
            return server
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            raise
    
    def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        attachments: Optional[List[tuple]] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content of email
            attachments: List of (filename, file_data) tuples
        
        Returns:
            bool: True if sent successfully
        """
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Attach files if provided
            if attachments:
                for filename, file_data in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename= {filename}",
                    )
                    message.attach(part)
            
            # Send email
            server = self._create_connection()
            server.send_message(message)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, user_name: str) -> bool:
        """Send password reset email"""
        
        # FIXED: Use the frontend URL from settings (already includes /smartJobFinder/frontend path)
        reset_link = f"{self.frontend_url}/reset-password.html?token={reset_token}"
        
        # Log the reset link for debugging - THIS SHOULD SHOW THE CORRECT PATH
        logger.info(f"Password reset link generated: {reset_link}")
        print(f"🔗 DEBUG - Reset link: {reset_link}")  # Extra debug output
        
        subject = "Reset Your Password - Smart Job Finder"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #0096C7 0%, #0077B6 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 30px;
                    background: #0096C7;
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>We received a request to reset your password for your Smart Job Finder account.</p>
                    <p>Click the button below to reset your password:</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #0096C7;">{reset_link}</p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <p>If you didn't request this password reset, please ignore this email or contact support if you have concerns.</p>
                    <p>Best regards,<br>Smart Job Finder Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Smart Job Finder. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_application_confirmation(
        self, 
        to_email: str, 
        user_name: str,
        job_title: str,
        company: str
    ) -> bool:
        """Send application confirmation email"""
        
        subject = f"Application Received - {job_title} at {company}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .job-details {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Application Submitted Successfully!</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Thank you for applying! We've received your application and it's now under review.</p>
                    <div class="job-details">
                        <h3>{job_title}</h3>
                        <p><strong>Company:</strong> {company}</p>
                        <p><strong>Status:</strong> Under Review</p>
                    </div>
                    <p>We'll notify you once the employer reviews your application.</p>
                    <p>In the meantime, you can:</p>
                    <ul>
                        <li>Browse more job opportunities</li>
                        <li>Update your profile</li>
                        <li>Track your applications in your dashboard</li>
                    </ul>
                    <p>Best regards,<br>Smart Job Finder Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_application_status_update(
        self,
        to_email: str,
        user_name: str,
        job_title: str,
        company: str,
        new_status: str
    ) -> bool:
        """Send application status update email"""
        
        status_messages = {
            "reviewed": "Your application has been reviewed",
            "shortlisted": "Congratulations! You've been shortlisted",
            "accepted": "Congratulations! Your application has been accepted",
            "rejected": "Application Update"
        }
        
        subject = f"{status_messages.get(new_status, 'Application Update')} - {job_title}"
        
        status_colors = {
            "reviewed": "#0dcaf0",
            "shortlisted": "#0096C7",
            "accepted": "#10b981",
            "rejected": "#6c757d"
        }
        
        color = status_colors.get(new_status, "#0096C7")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: {color};
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .status-badge {{
                    background: {color};
                    color: white;
                    padding: 10px 20px;
                    border-radius: 50px;
                    display: inline-block;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Application Status Update</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Your application for <strong>{job_title}</strong> at <strong>{company}</strong> has been updated.</p>
                    <div style="text-align: center;">
                        <span class="status-badge">{new_status.upper()}</span>
                    </div>
                    <p>Log in to your dashboard to view more details and track your application progress.</p>
                    <p>Best regards,<br>Smart Job Finder Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        
        subject = "Welcome to Smart Job Finder!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #0096C7 0%, #0077B6 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Smart Job Finder! 🎉</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>Thank you for joining Smart Job Finder! We're excited to help you find your dream job.</p>
                    <h3>Get Started:</h3>
                    <ul>
                        <li>Complete your profile</li>
                        <li>Upload your CV/Resume</li>
                        <li>Browse thousands of job opportunities</li>
                        <li>Apply with one click</li>
                    </ul>
                    <p>Our AI-powered system will recommend jobs that match your skills and experience.</p>
                    <p>Best regards,<br>Smart Job Finder Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)


# Create singleton instance
email_service = EmailService()