from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import CustomTokenObtainPairView, UserProfileView, LogoutView, RegisterView, ChangePasswordView
from .team_views import TenantMembershipViewSet, TenantInvitationViewSet
from .org_views import TenantViewSet, ContextTypeViewSet, EnvironmentViewSet
from .password_views import PasswordResetRequestView, PasswordResetConfirmView

router = DefaultRouter()
router.register(r'team/members', TenantMembershipViewSet, basename='team-members')
router.register(r'team/invitations', TenantInvitationViewSet, basename='team-invitations')
router.register(r'organization/tenant', TenantViewSet, basename='tenant')
router.register(r'organization/context-types', ContextTypeViewSet, basename='context-types')
router.register(r'organization/environments', EnvironmentViewSet, basename='environments')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/me/', UserProfileView.as_view(), name='user_profile'),
    path('auth/password-change/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('', include(router.urls)),
]
