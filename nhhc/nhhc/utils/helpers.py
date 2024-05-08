import os

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from loguru import logger
from rest_framework import status


def get_status_code_for_unauthorized_or_forbidden(request: HttpRequest) -> int:
    """
    Determine the appropriate HTTP status code for unauthorized or forbidden requests.

    Utilty Helper function takes in an HTTP request object and checks if the user associated with the request is authenticated.
    If the user is not authenticated, it returns HTTP status code 401 (Unauthorized). If the user is authenticated but
    does not have permission to access the requested resource, it returns HTTP status code 403 (Forbidden).

    Args:
        request (HttpRequest): An HTTP request object representing the request being processed.

    Returns:
        int: The HTTP status code to be returned based on the authentication status of the user.
    """
    return status.HTTP_401_UNAUTHORIZED if not request.user.is_authenticated else status.HTTP_403_FORBIDDEN


def get_content_for_unauthorized_or_forbidden(request: HttpRequest) -> bytes:
    """
    Utilty Helper function that returns a message based on the user's authentication status.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        bytes: A message indicating whether the user must be logged in or an admin to complete the request.
    """
    return bytes("You Must Be Logged In To Complete This Request", "utf-8") if not request.user.is_authenticated else bytes("You Must Be An Admin In To Complete This Request", "utf-8")


def send_new_user_credentials(new_user_email: str, new_user_first_name: str, password, username) -> HttpResponse:
    """
    Internal Non-Rendering View Function to send email notification of user name and password

    Args:
        new_user: Employee Instance of Employee
        password: str Autogenerated Plaintext Password
        username: str Username for the newly created account

    Returns:
        bool - True of the email was successdfully send. 200  HTTP Status Code if successful or 400  Bad Request if not successful and logs a JSON Error object with details

    """
    try:
        email_from = settings.EMAIL_HOST_USER
        sender_email = os.getenv("NOTIFICATION_SENDER_EMAIL")
        recipient_email = [new_user_email]
        sender_password = os.getenv("EMAIL_ACCT_PASSWORD")
        subject = f"Welcome to Nett Hands - {new_user_first_name}!"
        content = f"Welcome to Nett Hands, Please Login Your New Employee Account at https://www.netthandshome.care/login/ and Complete Onboarding Information in the Personal Information Section:\n Username = {username} \n Password = {password} \n You Will Be Prompted to change the password on first logging in!\n Welcome to the Family, {new_user_first_name}! \n "
        send_mail(subject, content, email_from, recipient_email)
        return HttpResponse(
            status=status.HTTP_200_OK,
            content=bytes('{"status": "SENT", "username": username}', "utf-8"),
        )
    except Exception as e:
        logger.error(f"Unable to Send New User Credentials...{e}")
        return HttpResponse(
            status=status.HTTP_400_BAD_REQUEST,
            content=bytes('{"status": "FAIL", "error": e}', "utf-8"),
        )


class CachedTemplateView(TemplateView):
    @classmethod
    def as_view(cls, **initkwargs):  # @NoSelf
        return cache_page(settings.CACHE_TTL)(super(CachedTemplateView, cls).as_view(**initkwargs))


# Decorator to Exponetiually Retry Certain Failures.
def exponentially_retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    Args:
        ExceptionToCheck(Exception): the exception to check. may be a tuple of exceptions to check
        tries(int): number of times to try (not retry) before giving up
        delay(int): initial delay between retries in seconds
        backoff(int): backoff multiplier e.g. value of 2 will double the delay
        logger(logger instance): logger to use. If None, print
    Returns:
        None
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck:
                    msg = "%s, Retrying in %d seconds..." % (str(ExceptionToCheck), mdelay)
                    if logger:
                        # logger.exception(msg) # would print stack trace
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry
