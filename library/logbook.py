from filelock import FileLock
import traceback
import datetime
import inspect
import os

class LogBookHandler:
    def __init__(self, system_name, logfile="logs/{{TIME}}.log"):
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        if system_name is not None:
            self.system_name = system_name
        else:
            try:
                # Try to get the caller's filename
                frame = inspect.stack()[1]
                self.system_name = os.path.basename(frame.filename)
            except (IndexError, AttributeError, RuntimeError):
                self.system_name = "unknown"
        self.logfile = LogBookHandler._parse_log_file(logfile)
        self.lockfile = self.logfile + ".lock"

    @staticmethod
    def _parse_log_file(log_file):
        logfile = log_file.replace(
            "{{TIME}}", str(datetime.datetime.now().strftime("%Y-%m-%d"))
        ).replace(
            "{{TIMENOW}}", str(datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S"))
        )
        return logfile

    def _write_locked(self, logline):
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        lock = FileLock(self.lockfile, timeout=10)
        with lock:
            try:
                with open(self.logfile, "a") as logfile:
                    logfile.write(logline)
            except UnicodeEncodeError:
                with open(self.logfile, "ab") as logfile:
                    logfile.write(logline.encode("utf-8"))

    def info(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logline = f"{now} [INFO] [{self.system_name}] {message}\n"
        self._write_locked(logline)

    def warning(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        function_name = frame.f_code.co_name
        line_number = frame.f_lineno
        logline = (
            f"{now} [WARNING] [{self.system_name}] {message} | "
            f"Location {filename}:{line_number} in {function_name}\n"
        )
        self._write_locked(logline)

    def error(self, message=None, exception=True, do_print=True):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if exception is True:
            trace = traceback.format_exc()
        elif isinstance(exception, BaseException):
            # Format the passed exception instance
            trace = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        elif exception:
            # If exc_info is truthy but not an exception, just str it
            trace = str(exception)
        else:
            trace = "No exception info provided."

        full_message = f"{message}\n{trace}" if message else trace
        logline = f"{now} [ERROR] [{self.system_name}] {full_message}\n"
        self._write_locked(logline)

        if do_print:
            print(full_message)

    def debug(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logline = f"{now} [DEBUG] [{self.system_name}] {message}\n"
        self._write_locked(logline)

    def critical(self, message):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        function_name = frame.f_code.co_name
        line_number = frame.f_lineno
        logline = (
            f"{now} [CRITICAL] [{self.system_name}] {message}\n"
            f"Location {filename}:{line_number} in {function_name}\n"
        )
        self._write_locked(logline)
