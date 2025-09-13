from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.hashers import make_password
from .models import EmailOTP
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """Service for handling OTP generation, sending, and verification"""
    
    @staticmethod
    def send_otp_email(email, username, first_name, last_name, password, invite_code):
        """
        Generate and send OTP email for registration verification
        Store user registration data temporarily
        """
        try:
            # Clean up any existing OTPs for this email
            EmailOTP.cleanup_expired()
            EmailOTP.objects.filter(email=email, is_verified=False).delete()
            
            # Generate new OTP
            otp_code = EmailOTP.generate_otp()
            
            # Create OTP record with registration data
            otp_record = EmailOTP.objects.create(
                email=email,
                otp_code=otp_code,
                username=username,
                first_name=first_name,
                last_name=last_name,
                password_hash=make_password(password),
                invite_code=invite_code
            )
            
            # Send email
            subject = 'Verify Your Email - GrwComm Registration'
            
            # Create email content
            message_lines = [
                f"Hi {first_name},",
                f"",
                f"Welcome to GrwComm! To complete your registration, please verify your email address.",
                f"",
                f"Your verification code is: {otp_code}",
                f"",
                f"This code will expire in 10 minutes for security reasons.",
                f"",
                f"If you didn't request this registration, please ignore this email.",
                f"",
                f"Best regards,",
                f"The GrwComm Team"
            ]
            
            message = '\n'.join(message_lines)
            
            # Send the email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"OTP email sent successfully to {email}")
            return True, otp_record
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def verify_otp(email, entered_otp):
        """Verify OTP and return the registration data if valid"""
        try:
            # Get the latest OTP for this email
            otp_record = EmailOTP.objects.filter(
                email=email,
                is_verified=False
            ).order_by('-created_at').first()
            
            if not otp_record:
                return False, "No valid OTP found for this email."
            
            if not otp_record.is_valid():
                if otp_record.is_expired():
                    return False, "OTP has expired. Please request a new one."
                elif otp_record.attempts >= otp_record.max_attempts:
                    return False, "Too many failed attempts. Please request a new OTP."
                else:
                    return False, "OTP is no longer valid."
            
            # Verify the OTP
            if otp_record.verify_otp(entered_otp):
                return True, otp_record
            else:
                remaining_attempts = otp_record.max_attempts - otp_record.attempts
                if remaining_attempts > 0:
                    return False, f"Invalid OTP. {remaining_attempts} attempts remaining."
                else:
                    return False, "Invalid OTP. No more attempts remaining. Please request a new OTP."
                    
        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {str(e)}")
            return False, "An error occurred while verifying OTP."
    
    @staticmethod
    def resend_otp(email):
        """Resend OTP for existing registration attempt"""
        try:
            # Get the latest OTP record for this email
            existing_otp = EmailOTP.objects.filter(
                email=email,
                is_verified=False
            ).order_by('-created_at').first()
            
            if not existing_otp:
                return False, "No pending registration found for this email."
            
            # Generate new OTP
            new_otp_code = EmailOTP.generate_otp()
            
            # Update the existing record
            existing_otp.otp_code = new_otp_code
            existing_otp.attempts = 0  # Reset attempts
            existing_otp.save()
            
            # Send new OTP email
            subject = 'New Verification Code - GrwComm Registration'
            
            message_lines = [
                f"Hi {existing_otp.first_name},",
                f"",
                f"Here's your new verification code for GrwComm registration:",
                f"",
                f"Your verification code is: {new_otp_code}",
                f"",
                f"This code will expire in 10 minutes for security reasons.",
                f"",
                f"Best regards,",
                f"The GrwComm Team"
            ]
            
            message = '\n'.join(message_lines)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"OTP resent successfully to {email}")
            return True, "New verification code sent successfully."
            
        except Exception as e:
            logger.error(f"Failed to resend OTP to {email}: {str(e)}")
            return False, "Failed to send new verification code."