from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer

User = get_user_model()

class PasswordResetRequestView(generics.GenericAPIView):
    """
    Request a password reset email.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # In a real app, send email here
            # For now, we'll print the reset link to the console and return it
            from django.conf import settings
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_link = f"{frontend_url}/reset-password?uid={uid}&token={token}"
            print(f"\n[PASSWORD RESET] Link for {email}: {reset_link}\n")
            
            return Response(
                {
                    "message": "Password reset email sent.",
                    "mock_link": reset_link
                },
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            # Don't reveal user existence
            return Response(
                {"message": "Password reset email sent."},
                status=status.HTTP_200_OK
            )


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Reset password using token and uid.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        uidb64 = serializer.validated_data['uidb64']
        password = serializer.validated_data['password']

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                return Response(
                    {"message": "Password has been reset successfully."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST
            )
