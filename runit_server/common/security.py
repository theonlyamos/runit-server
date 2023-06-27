from ..models import User
from .utils import Utils


#def authenticate(password: str, user_password: str)-> bool:
#    return Utils.check_hashed_password(password, user_password)

def authenticate(email: str, password: str):
    '''
    Function for authenticating user

    @param email Email Address
    @param password Password
    @return User Instance or None
    '''
    user = User.get_by_email(email)
    if user:
        if Utils.check_hashed_password(password, user.password):
            return user
    return None


def identity(payload):
    user_id = payload['identity']
    return User.get(user_id)
