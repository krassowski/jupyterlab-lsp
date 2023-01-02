from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options


def create_firefox_profile_logging_to_stdout():
    """Returns path to new profile"""
    profile = FirefoxProfile()
    profile.set_preference("devtools.console.stdout.content", True)
    profile.update_preferences()
    return profile.path
