import datetime
import os
import time
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from retrying import retry
import hashlib

CONFIG_PATH = Path(__file__).parent.parent.parent / 'configs' / 'configs.yaml'
assert CONFIG_PATH.exists(), f"CONFIG FILE doesn't exist. CHECK: {CONFIG_PATH}"

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    configs = yaml.load(f, Loader=yaml.FullLoader)

"""
ENVIRONMENT SETTINGS
"""
DEFAULT_CHROMEDRIVER_PATH = configs.get("environment", {}).get("default_chromedriver_path")
DEFAULT_CHROMEDRIVER_VERSION = configs.get("environment", {}).get("default_chromedriver_version", 118)
assert DEFAULT_CHROMEDRIVER_PATH, 'DEFAULT Chromedriver path doesnt exist. Please update your configs.yaml'

"""
Endpoints（页面入口地址）
"""
# End-points:
ENDPOINTS = configs.get("endpoints", {})

"""
RUNTIME_SETTINGS
"""
GLOBAL_TIMEWAIT = configs.get("runtime_settings", {}).get("global_time_wait", 1)
DEFAULT_CHROMEDRIVER_DOWNLOAD_PATH = configs.get("runtime_settings", {}).get("default_chrome_download_path")

"""
General Exceptions
"""


class GeneralException(Exception):
    class PreCrawlPreparationException(Exception):
        class LoginFailedException(Exception):
            pass

        class FailToSwitchToEndpointPage(Exception):
            pass

        class MethodNotImplemented(Exception):
            pass

    class RuntimeException(Exception):
        class ElementMissing(Exception):
            pass

        class StepNotSuccess(Exception):
            pass

        class InputFormatError(Exception):
            pass

        class ParamMissingError(Exception):
            pass

        class ParamInvalid(Exception):
            pass

    class PostCrawlException(Exception):
        class RawDataInvalid(Exception):
            pass


"""
General Utils
"""


@retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000)
def click_btn(driver_instance, btn_name, btn_class='*', exception_class=Exception, parent_xpath=None,
              target_attribute='text()'):
    try:
        if parent_xpath:
            parent_element = WebDriverWait(driver_instance, 60, 0.1).until(
                EC.presence_of_element_located((By.XPATH, parent_xpath))
            )
            target_btn = parent_element.find_element(By.XPATH,
                                                     f".//{btn_class}[contains({target_attribute}, '{btn_name}')]")
        else:
            target_btns = WebDriverWait(driver_instance, 60, 0.1).until(
                EC.visibility_of_any_elements_located(
                    (By.XPATH, f"//{btn_class}[contains({target_attribute}, '{btn_name}')]"))
            )
            if len(target_btns) > 1:
                logger.warning("Found multiple target inputs. Will select the 1st one.")
            target_btn = target_btns[0]
        # logger.debug(f"Found target btn: {target_btn}, full xpath: {target_btn.get_attribute('outerHTML')}")
        target_btn.click()
        logger.success(f'{btn_name} clicked.')
    except Exception as e:
        logger.error(f"Fail to find btn {btn_name}: {str(e)}")
        raise exception_class(f"Fail to find btn {btn_name}: {str(e)}")


@retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000)
def key_in_input(driver_instance, input_name, keyin_value, exception_class=Exception, parent_xpath=None,
                 target_attribute='text()'):
    try:
        if parent_xpath:
            parent_element = WebDriverWait(driver_instance, 60, 0.1).until(
                EC.presence_of_element_located((By.XPATH, parent_xpath))
            )
            target_input = parent_element.find_element(By.XPATH,
                                                       f".//input[contains({target_attribute}, '{input_name}')]")
        else:
            target_inputs = WebDriverWait(driver_instance, 60, 0.1).until(
                EC.visibility_of_any_elements_located(
                    (By.XPATH, f"//input[contains({target_attribute}, '{input_name}')]"))
            )
            if len(target_inputs) > 1:
                logger.warning("Found multiple target inputs. Will select the 1st one.")
            target_input = target_inputs[0]

        target_input.clear()
        target_input.send_keys(keyin_value)
        logger.success(f'{input_name} keyed in {keyin_value}.')
    except Exception as e:
        logger.error(f"Fail to find input {input_name}: {str(e)}")
        raise exception_class(f"Fail to find input {input_name}: {str(e)}")


def if_flag_element_exists(driver_instance, flag_element_xpath, endpoint=None, timeout=30):
    if endpoint:
        driver_instance.get(endpoint)
    try:
        WebDriverWait(driver_instance, timeout, 0.1).until(
            EC.presence_of_element_located((By.XPATH, flag_element_xpath))
        )
        return True
    except:
        return False


def set_date_element(driver_instance, date_input_xpath, date_str, date_format='%Y-%m-%d'):
    try:
        date_elements = WebDriverWait(driver_instance, 10, 0.1).until(
            EC.visibility_of_any_elements_located((By.XPATH, date_input_xpath))
        )
        if len(date_elements) > 1:
            logger.warning("Found multiple target inputs. Will select the 1st one.")
        date_element = date_elements[0]
    except Exception as e:
        raise GeneralException.RuntimeException.StepNotSuccess(str(e))
    try:
        date_datetime = datetime.datetime.strptime(date_str, date_format)
    except Exception as e:
        raise GeneralException.RuntimeException.InputFormatError(str(e))
    driver_instance.execute_script("arguments[0].removeAttribute('readonly');", date_element)
    date_element.send_keys(Keys.CONTROL, 'a')
    date_element.send_keys(date_datetime.strftime(date_format))
    webdriver.ActionChains(driver_instance).send_keys(Keys.ENTER).perform()
    webdriver.ActionChains(driver_instance).send_keys(Keys.ESCAPE).perform()
    current_date = date_element.get_attribute('value')
    if current_date != date_str:
        raise GeneralException.RuntimeException.StepNotSuccess(
            f"Fail to set start_date to {date_str}. Current: {current_date}")


"""
chromedriver utils
"""


def modify_chromedriver_download_path(driver_instance, target_download_path: str):
    os.makedirs(target_download_path, exist_ok=True)
    driver_instance.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    params = {'cmd': 'Page.setDownloadBehavior',
              'params': {'behavior': 'allow', 'downloadPath': target_download_path}}
    logger.debug(f"Set chromedriver download path to {target_download_path}")
    driver_instance.execute("send_command", params)


def downloading_sentinel(target_file_path: str, timeout_seconds: int = 10, poll_interval: int = 1):
    logger.info("Start downloading sentinel.")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        if Path(target_file_path).exists():
            return
        logger.debug(f"Not yet downloaded. {target_file_path}")
        time.sleep(poll_interval)

    # 如果超时仍未下载完成，则抛出异常
    # raise GeneralException.RuntimeException.StepNotSuccess(f"File not downloaded within {timeout_seconds} seconds.")
    logger.warning(f"File not downloaded within {timeout_seconds} seconds.")


"""
MD5
"""


def md5_hash(input_string):
    # 创建 MD5 哈希对象
    md5_hash_obj = hashlib.md5()

    # 使用 update 方法逐步更新哈希对象
    # 这样可以处理较长的输入字符串而不必一次性加载整个字符串到内存中
    md5_hash_obj.update(input_string.encode('utf-8'))

    # 获取十六进制表示的哈希值
    md5_hash_value = md5_hash_obj.hexdigest()

    return md5_hash_value
