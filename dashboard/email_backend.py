from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    """
    Custom SMTP Email Backend to override the local_hostname.
    This fixes issues where the system hostname contains invalid characters 
    (like commas) that are rejected by some SMTP servers (e.g., Gmail).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force a safe local hostname
        self.local_hostname = 'localhost'
    def open(self):
        if self.connection:
            return False
        try:
            self.connection = self.connection_class(
                self.host, self.port, local_hostname='localhost', timeout=self.timeout
            )
            if self.use_tls:
                self.connection.starttls()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False
