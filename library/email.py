from library.logbook import LogBookHandler
from library.auth import get_ssl_filepaths
from email.mime.text import MIMEText
from library.settings import get
from typing import List, Dict
import smtplib
import ssl

logbook = LogBookHandler("emailing")

cert_path, key_path = get_ssl_filepaths()
ssl_context = ssl.create_default_context()
ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

class email:
    def __init__(self, recipient: Dict[str, str, str] = None, recipients: List[Dict[str, str, str]] = None):  # dict is: recipient, subject line, message
        if not recipient and recipients:
            self.recipients = recipients
        elif not recipients and recipient:
            self.recipient = recipient

    def send(self):
        if self.recipient:
            return self.__send_email()
        else:
            return self.__bulk_send_email

    def __send_email(self):
        sender = get.system_email()
        password = get.sys_email_password()

        msg = MIMEText(self.recipient['message'])
        msg["Subject"] = self.recipient['subject_line']
        msg["From"] = sender
        msg["To"] = self.recipient

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_context) as server:
                server.login(sender, password)
                server.send_message(msg)
        except Exception as err:
            logbook.error(f"Failed to send email to {self.recipient}: {err}", err)
            return False

        logbook.info(f"Email sent to {msg['To']}!")
        return True

    def __bulk_send_email(self):
        sender = get.system_email()
        password = get.sys_email_password()
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

        results = {}
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_context) as server:
            server.login(sender, password)
            for recipient in self.recipients:
                try:
                    msg = MIMEText(recipient['message'])
                    msg["Subject"] = recipient['subject_line']
                    server.send_message(msg)
                    results[recipient] = True
                except Exception as e:
                    logbook.error(f"Failed to send email to {recipient}: {e}")
                    results[recipient] = False

        return results