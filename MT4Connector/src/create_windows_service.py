"""
Windows Service for MT4 Connector
Allows the connector to run as a Windows service
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import main as run_connector
from src.config import LOGS_DIR

class MT4ConnectorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MT4Connector"
    _svc_display_name_ = "MT4 Connector Service"
    _svc_description_ = "Connects MT4 to process EA signals automatically"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_running = True
        
        # Set up logging
        log_file = os.path.join(LOGS_DIR, "mt4_connector_service.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MT4ConnectorService')
        
    def SvcStop(self):
        """Stop the service"""
        self.logger.info('Stopping MT4 Connector Service')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False
        
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.logger.info('Starting MT4 Connector Service')
        self.main()
        
    def main(self):
        """Main service loop"""
        try:
            # Set environment variable to skip interactive mode
            os.environ['MT4_SERVICE_MODE'] = 'True'
            os.environ['MOCK_MODE'] = 'False'
            
            self.logger.info('MT4 Connector Service started successfully')
            
            # Run the connector
            while self.is_running:
                try:
                    run_connector()
                except Exception as e:
                    self.logger.error(f'Error in connector: {e}')
                    time.sleep(30)  # Wait before retry
                    
                if win32event.WaitForSingleObject(self.hWaitStop, 0) == win32event.WAIT_OBJECT_0:
                    break
                    
        except Exception as e:
            self.logger.error(f'Service error: {e}')
            servicemanager.LogErrorMsg(f'MT4 Connector Service Error: {e}')

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Service is being started by Windows
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MT4ConnectorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line arguments for installing/starting/stopping/removing
        win32serviceutil.HandleCommandLine(MT4ConnectorService)