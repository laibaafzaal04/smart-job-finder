# app/models/__init__.py
from app.models.user import (
    UserBase, UserRegister, UserLogin, UserResponse, Token,
    ForgotPasswordRequest, ResetPasswordRequest, UserRole
)

# Import profile models conditionally to avoid circular imports
try:
    from app.models.profile import (
        ProfileCreate, ProfileResponse,
        EducationLevel, ExperienceLevel
    )
    __all__ = [
        'UserBase', 'UserRegister', 'UserLogin', 'UserResponse', 'Token',
        'ForgotPasswordRequest', 'ResetPasswordRequest', 'UserRole',
        'ProfileCreate', 'ProfileResponse',
        'EducationLevel', 'ExperienceLevel'
    ]
except ImportError:
    __all__ = [
        'UserBase', 'UserRegister', 'UserLogin', 'UserResponse', 'Token',
        'ForgotPasswordRequest', 'ResetPasswordRequest', 'UserRole'
    ]