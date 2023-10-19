from passlib.hash import pbkdf2_sha512
import re


class Utils(object):

    @staticmethod
    def email_is_valid(email: str)-> bool:
        """
        Checks if the provided email is a valid
        email address
        
        :param email: Email Address
        
        :return: True if email is valid, False otherwise
        """
        
        email_address_matcher = re.compile('^[\w-]+@([\w-]+\.)+[\w]+$')
        return True if email_address_matcher.match(email) else False

    @staticmethod
    def hash_password(password: str)-> str:
        """
        Hashes a password using pbkdf2_sha512
        
        :param password: The password from the login/register form
        
        :return: A sha512->pbkdf2_sha512 encrypted password
        """
        return pbkdf2_sha512.encrypt(password)

    @staticmethod
    def check_hashed_password(password: str, hashed_password: str)-> bool:
        """
        Checks that the password the user sent matches that of the database.
        The datase password is encrypted more than the user's password at this stage.
        
        :param password: password
        :param hashed_password: pbkdf2_sha512 encrytped password
        
        :return: True if passwords match, False otherwise
        """
        return pbkdf2_sha512.verify(password, hashed_password)