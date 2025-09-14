from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from .models import PasswordResetToken
import logging
import os

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for handling password reset functionality"""
    
    @staticmethod
    def send_reset_email(email):
        """
        Generate and send password reset email
        """
        try:
            # Get user
            user = User.objects.get(email=email)
            
            # Clean up any existing tokens for this user
            PasswordResetToken.cleanup_expired()
            PasswordResetToken.objects.filter(user=user, is_used=False).delete()
            
            # Generate new token
            token = PasswordResetToken.generate_token()
            
            # Create token record
            reset_token = PasswordResetToken.objects.create(
                user=user,
                token=token
            )
            
            # Generate reset URL
            site_url = os.getenv('SITE_URL', 'http://localhost:8000')
            reset_url = f"{site_url}/auth/password-reset/confirm/{token}/"
            
            # Send email
            subject = 'Reset Your Password - GrwComm'
            
            # Create email content
            message_lines = [
                f"Hi {user.first_name or user.username},",
                f"",
                f"We received a request to reset your password for your GrwComm account.",
                f"",
                f"Click the button below to reset your password:",
                f"{reset_url}",
                f"",
                f"This link will expire in 24 hours for security reasons.",
                f"",
                f"If you didn't request this password reset, please ignore this email.",
                f"Your password will remain unchanged.",
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
            
            logger.info(f"Password reset email sent successfully to {email}")
            return True, "Password reset email sent successfully"
            
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            # Return success to prevent email enumeration
            return True, "If an account with this email exists, you'll receive reset instructions"
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False, "Failed to send password reset email"
    
    @staticmethod
    def verify_token(token):
        """Verify password reset token"""
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token,
                is_used=False
            )
            
            if reset_token.is_valid():
                return True, reset_token
            else:
                if reset_token.is_expired():
                    return False, "Password reset link has expired. Please request a new one."
                else:
                    return False, "Password reset link is no longer valid."
                    
        except PasswordResetToken.DoesNotExist:
            return False, "Invalid password reset link."
        except Exception as e:
            logger.error(f"Error verifying password reset token {token}: {str(e)}")
            return False, "An error occurred while verifying the reset link."
    
    @staticmethod
    def reset_password(token, new_password):
        """Reset user password using token"""
        try:
            success, result = PasswordResetService.verify_token(token)
            
            if not success:
                return False, result
            
            reset_token = result
            user = reset_token.user
            
            # Update user password using Django's set_password method
            old_password_hash = user.password
            user.set_password(new_password)
            user.save()
            
            # Verify password was changed
            if user.password == old_password_hash:
                logger.error(f"Password not updated for user {user.email}")
                return False, "Failed to update password"
            
            # Invalidate all existing sessions for this user for security
            try:
                for session in Session.objects.all():
                    session_data = session.get_decoded()
                    if session_data.get('_auth_user_id') == str(user.id):
                        session.delete()
                        logger.info(f"Invalidated session for user {user.email}")
            except Exception as session_error:
                logger.warning(f"Could not invalidate sessions for user {user.email}: {session_error}")
            
            # Mark token as used
            reset_token.is_used = True
            reset_token.save()
            
            logger.info(f"Password reset successfully for user {user.email}. Hash changed from {old_password_hash[:20]}... to {user.password[:20]}...")
            return True, "Password has been reset successfully"
            
        except Exception as e:
            logger.error(f"Error resetting password with token {token}: {str(e)}")
            return False, "An error occurred while resetting password"