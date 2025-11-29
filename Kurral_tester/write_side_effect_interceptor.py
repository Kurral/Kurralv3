"""
Write Side Effect Interceptor for Replay
Blocks specific write operations that we can definitively identify:
- Email sending (smtplib)
- File writes (open in write modes)
- Environment variable writes

Does NOT block HTTP methods - let them through (can't distinguish read vs write POST)
"""
import smtplib
import builtins
import os
from typing import Any, Optional
from contextlib import contextmanager


class WriteSideEffectInterceptor:
    """
    Intercepts and blocks specific write operations during replay.
    Only blocks operations we can definitively identify as writes.
    Does NOT block HTTP methods - those are handled by tool caching.
    """
    
    def __init__(self):
        self.original_smtp_ssl = None
        self.original_smtp = None
        self.original_open = None
        self.original_environ_setitem = None
        self.active = False
    
    def _stub_smtp_ssl(self, host, port, context=None, **kwargs):
        """Stub for smtplib.SMTP_SSL - blocks email sending"""
        print(f"[WRITE BLOCKED] smtplib.SMTP_SSL({host}, {port}) - Email sending blocked during replay")
        
        class MockSMTP:
            def __enter__(self):
                return self
            
            def __exit__(self, *args, **kwargs):
                return False
            
            def login(self, *args, **kwargs):
                print(f"[WRITE BLOCKED] SMTP.login() - Blocked during replay")
                return True
            
            def send_message(self, *args, **kwargs):
                print(f"[WRITE BLOCKED] SMTP.send_message() - Email send blocked during replay")
                return {}
            
            def sendmail(self, *args, **kwargs):
                print(f"[WRITE BLOCKED] SMTP.sendmail() - Email send blocked during replay")
                return {}
        
        return MockSMTP()
    
    def _stub_open(self, file, mode='r', *args, **kwargs):
        """Intercept open() - block write/append modes, allow read modes"""
        # Block write operations
        write_modes = {'w', 'a', 'x', 'w+', 'a+', 'x+', 'wb', 'ab', 'xb', 'w+b', 'a+b', 'x+b'}
        if mode in write_modes:
            print(f"[WRITE BLOCKED] open('{file}', mode='{mode}') - File write blocked during replay")
            
            class MockFile:
                def write(self, *args, **kwargs):
                    pass
                
                def writelines(self, *args, **kwargs):
                    pass
                
                def flush(self, *args, **kwargs):
                    pass
                
                def close(self, *args, **kwargs):
                    pass
                
                def __enter__(self):
                    return self
                
                def __exit__(self, *args, **kwargs):
                    return False
            
            return MockFile()
        
        # Allow read operations - pass through to original
        return self.original_open(file, mode, *args, **kwargs)
    
    def _stub_environ_setitem(self, key, value):
        """Block environment variable writes"""
        print(f"[WRITE BLOCKED] os.environ['{key}'] = ... - Environment variable write blocked during replay")
        # Don't actually set it
    
    def activate(self):
        """Activate write-side-effect interception"""
        if self.active:
            return
        
        # Save originals
        self.original_smtp_ssl = smtplib.SMTP_SSL
        self.original_smtp = getattr(smtplib, 'SMTP', None)
        self.original_open = builtins.open
        self.original_environ_setitem = os.environ.__setitem__
        
        # Patch only specific write operations we can definitively identify
        smtplib.SMTP_SSL = self._stub_smtp_ssl
        if self.original_smtp:
            smtplib.SMTP = self._stub_smtp_ssl
        
        builtins.open = self._stub_open
        os.environ.__setitem__ = self._stub_environ_setitem
        
        self.active = True
        print("[REPLAY MODE] Write side-effect interception activated (email, file writes blocked)")
    
    def deactivate(self):
        """Deactivate write-side-effect interception"""
        if not self.active:
            return
        
        # Restore originals
        if self.original_smtp_ssl:
            smtplib.SMTP_SSL = self.original_smtp_ssl
        if self.original_smtp:
            smtplib.SMTP = self.original_smtp
        if self.original_open:
            builtins.open = self.original_open
        if self.original_environ_setitem:
            os.environ.__setitem__ = self._stub_environ_setitem
        
        self.active = False
    
    @contextmanager
    def intercept(self):
        """Context manager to temporarily enable write interception"""
        try:
            self.activate()
            yield self
        finally:
            self.deactivate()


# Global interceptor instance
_interceptor = WriteSideEffectInterceptor()


def activate_write_interception():
    """Activate write-side-effect interception for replay"""
    _interceptor.activate()


def deactivate_write_interception():
    """Deactivate write-side-effect interception"""
    _interceptor.deactivate()


@contextmanager
def write_interception():
    """Context manager for write-side-effect interception"""
    with _interceptor.intercept():
        yield

