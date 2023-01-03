from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


def create_firefox_profile_logging_to_stdout(enable_logging=True):
    """Returns path to new profile logging to stdout (hence `geckodriver.log`)"""
    profile = FirefoxProfile()
    profile.set_preference("devtools.console.stdout.content", bool(enable_logging))
    profile.update_preferences()
    return profile.path
