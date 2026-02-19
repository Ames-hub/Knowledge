from modules.centralfiles.classes import centralfiles
from library.logbook import LogBookHandler
from email.mime.text import MIMEText
from library.settings import get
from typing import List
import smtplib
import ssl

logbook = LogBookHandler("emailing")
ssl_context = ssl.create_default_context()

class recipient_profile:
    def __init__(self, email: str, subjectline: str, message: str):
        self.email = email
        self.subjectline = subjectline
        self.message = message

class client_email:
    def __init__(self, recipient: recipient_profile = None, recipients: List[recipient_profile] = None):
        if recipient:
            self.recipient = recipient
        elif recipients:
            self.recipients = recipients
        else:
            raise ValueError("No recipients provided")

    def send(self):
        if hasattr(self, 'recipient'):
            return self.__send_email(self.recipient)
        else:
            return self.__bulk_send_email()

    def __send_email(self, recipient_obj: recipient_profile):
        sender = get.system_email()
        password = get.sys_email_password()

        msg = MIMEText(recipient_obj.message)
        msg["Subject"] = recipient_obj.subjectline
        msg["From"] = sender
        msg["To"] = recipient_obj.email

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_context) as server:
                server.login(sender, password)
                server.send_message(msg)
        except Exception as err:
            logbook.error(f"Failed to send email to {recipient_obj.email}: {err}", err)
            return False

        logbook.info(f"Email sent to {msg['To']}!")
        return True

    def __bulk_send_email(self):
        sender = get.system_email()
        password = get.sys_email_password()

        results = {}
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl_context) as server:
            server.login(sender, password)
            for rec in self.recipients:
                if not rec.email:
                    continue
                try:
                    msg = MIMEText(rec.message)
                    msg["Subject"] = rec.subjectline
                    msg["From"] = sender
                    msg["To"] = rec.email
                    server.send_message(msg)
                    results[rec.email] = True
                except Exception as e:
                    logbook.error(f"Failed to send email to {rec.email}: {e}")
                    results[rec.email] = False

        return results

    def parse_mail(self, text:str, recipient_email:str):
        """
        Docstring for parse_mail
        
        Parses the placeholders you may find in mail.

        :param text: The email text
        :type text: str
        :param recipient_email: The email of the person its being sent to.
        :type recipient_email: str
        """
        profile = centralfiles.get_profile(cfid=centralfiles.get_cfid_by_email(recipient_email))

        placeholders = {
            "<first_name>": profile['name'].split(" ")[0]
        }