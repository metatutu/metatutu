import smtplib
from email.utils import formataddr, formatdate
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from metatutu.logging import *

__all__ = ["Message", "Sender"]

class Message:
    """E-mail message."""
    def __init__(self):
        self.sender = (None, "")
        self.to = []
        self.cc = []
        self.bcc = []
        self.subject = ""
        self.attachments = []
        self.body = ("plain", "")
        self.timeval = None
        self.localtime = False
        self.usegmt = False
        self.importance = None
        self.sensitivity = None
        self.delivery_notification = False
        self.read_notification = False

    def set_sender(self, address, name=None):
        """Set sender.
        
        :param address: E-mail address of the sender.
        :param name: Name of the sender.
        """
        self.sender = (name, address)

    def add_receiver(self, address, name=None, type="to"):
        """Add a receiver.
        
        :param address: E-mail address of the receiver.
        :param name: Name of the receiver.
        :param type: Type of receiver.  Valid options are "to", "cc" and "bcc".
        """
        if type == "to":
            self.to.append((name, address))
        elif type == "cc":
            self.cc.append((name, address))
        elif type == "bcc":
            self.bcc.append((name, address))
    
    def add_receivers(self, receivers, type="to"):
        """Add receivers.
        
        :param receivers: List of receivers with items as (name, address).
        :param type: Type of receivers.  Valid options are "to", "cc" and "bcc".
        """
        if type == "to":
            self.to += receivers
        elif type == "cc":
            self.cc += receivers
        elif type == "bcc":
            self.bcc += receivers
    
    def set_subject(self, subject):
        """Set subject.
        
        :param subject: E-mail subject.
        """
        self.subject = subject

    def add_attachment(self, filepath, as_filename):
        """Add an attachment.
        
        :param filepath: The path of the file to be attached.
        :param as_filename: The filename to be displayed in the e-mail message.
        :returns: Returns True on success and False on failure.
        """
        data = FileSystemUtils.load_file_bytes(filepath)
        if data is None: return False
        self.attachments.append((data, as_filename))
        return True

    def set_body(self, body, type="plain"):
        """Set E-mail body.
        
        :param body: E-mail body.
        :param type: Body type.  Valid options are "plain" and "html".
        """
        if type == "plain":
            self.body = ("plain", body)
        elif type == "html":
            self.body = ("html", body)

    def set_date(self, timeval=None, localtime=False, usegmt=False):
        """Set date.
        
        :param timeval: Timestamp.  If it's None, use current time.
        :param localtime: Whether timeval is in local time or UTC.
        :param usegmt: Whether timezone is written out as ascii string.
        """
        self.timeval = timeval
        self.localtime = localtime
        self.usegmt = usegmt

    def set_importance(self, importance):
        """Set importance.
        
        :param importance: Valid options are None, "high" and "low".
        """
        self.importance = importance

    def set_sensitivity(self, sensitivity):
        """Set sensitivity.
        
        :param sensitivity: Valid options are None, "personal", "private" and "confidential".
        """
        self.sensitivity = sensitivity
    
    def get_sender_address(self):
        """Get sender's E-mail address."""
        if self.sender:
            return self.sender[1]
        else:
            return ""

    def get_receiver_addresses(self):
        """Get list of receivers' e-mail addresses."""
        addresses = []
        for item in self.to:
            address = item[1]
            if address not in addresses: addresses.append(address)
        for item in self.cc:
            address = item[1]
            if address not in addresses: addresses.append(address)
        for item in self.bcc:
            address = item[1]
            if address not in addresses: addresses.append(address)
        return addresses

    def get_formatted_message(self):
        """Create a formatted message object."""
        def format_address(item):
            name, address = item
            if name:
                return formataddr((Header(name, "utf-8").encode(), address))
            else:
                return address

        def format_addresses(items):
            addresses = []
            for item in items:
                addresses.append(format_address(item))
            return ",".join(addresses)

        # body
        body_type, body_content = self.body
        if body_type == "html":
            part_body = MIMEText(body_content, "html", "utf-8")
        else:
            part_body = MIMEText(body_content, "plain", "utf-8")

        if len(self.attachments) > 0:
            message = MIMEMultipart()
            message.attach(part_body)
        else:
            message = part_body

        # date
        message["Date"] = formatdate(self.timeval, self.localtime, self.usegmt)

        # sender
        message["From"] = format_address(self.sender)

        # receivers
        message["To"] = format_addresses(self.to)
        message["Cc"] = format_addresses(self.cc)

        # subject
        message["Subject"] = Header(self.subject, "utf-8")

        # importance
        if self.importance:
            importance = self.importance.lower()
            if importance == "high":
                message["X-Priority"] = "1"
                message["Importance"] = "high"
            elif importance == "low":
                message["X-Priority"] = "5"
                message["Importance"] = "low"

        # sensitivity
        if self.sensitivity:
            sensitivity = self.sensitivity.lower()
            if sensitivity == "personal":
                message["Sensitivity"] = "Personal"
            elif sensitivity == "private":
                message["Sensitivity"] = "Private"
            elif sensitivity == "confidential":
                message["Sensitivity"] = "Company-Confidential"

        # delivery notification
        if self.delivery_notification:
            message["Return-Receipt-To"] = format_address(self.sender)

        # read notification
        if self.read_notification:
            message["Disposition-Notification-To"] = format_address(self.sender)

        # attachments
        for attachment in self.attachments:
            att = MIMEApplication(attachment[0])
            att["Content-Type"] = "application/octet-stream"
            att.add_header("Content-Disposition", "attachment", filename=attachment[1])
            message.attach(att)

        #
        return message

class Sender(LoggerHelper):
    """Message sender."""
    def __init__(self):
        LoggerHelper.__init__(self)

        # config
        self.smtp_host = None
        self.smtp_ssl = True
        self.smtp_port = None
        self.smtp_user = None
        self.smtp_password = None

        # control
        self._client = None

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connect to SMTP server and login.
        
        :returns: Returns SMTP client handler on success and None on failure.
        """
        try:
            if self._client: return self._client

            # connect SMTP server
            self.debug("Connecting SMTP server...")
            if self.smtp_ssl:
                client = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                client = smtplib.SMTP(self.smtp_host, self.smtp_port)

            # login
            self.debug("Login to SMTP server...")
            result = client.login(self.smtp_user, self.smtp_password)
            print(result)
            if result is None:
                self.error("Login failed!")
                client.quit()
                return None
            if result[0] != 235:
                self.error("Login failed! ({})".format(result[0]))
                client.quit()
                return None
            self._client = client
            return self._client
        except Exception as ex:
            self.exception(ex)
            return None

    def disconnect(self):
        """Disconnect to SMTP server."""
        try:
            if self._client is None: return

            # disconnect SMTP server
            self.debug("Disconnecting SMTP server...")
            self._client.quit()
            self._client = None
        except:
            self._client = None

    @property
    def client(self):
        return self.connect()

    def send(self, message, reset_connection=False):
        """Send message.
        
        :param message: Message object.
        :param reset_connection: Whether to reset the connection.
        :returns: Returns True on success and False on failure.
        """
        try:
            # get client
            if reset_connection: self.disconnect()
            client = self.client
            if client is None: return False

            # send
            print("sending")
            client.sendmail(
                message.get_sender_address(),
                message.get_receiver_addresses(),
                message.get_formatted_message().as_string()
            )
            print("sent")

            #
            return True
        except Exception as ex:
            self.exception(ex)
            return False
