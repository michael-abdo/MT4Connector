"""
Enhanced trade execution logging for production deployment.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

# Configure logging
logger = logging.getLogger(__name__)

class TradeLogger:
    """Enhanced logging for trade execution and monitoring"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """Initialize trade logger"""
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / 'data' / 'logs' / 'trades'
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create separate log files for different types
        self.trade_log = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        self.error_log = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        self.audit_log = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Setup formatters
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup specialized loggers"""
        # Trade execution logger
        self.trade_logger = logging.getLogger('trade_execution')
        self.trade_logger.setLevel(logging.INFO)
        
        trade_handler = logging.FileHandler(self.trade_log)
        trade_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.trade_logger.addHandler(trade_handler)
        
        # Error logger
        self.error_logger = logging.getLogger('trade_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.FileHandler(self.error_log)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
        
        # Audit logger
        self.audit_logger = logging.getLogger('trade_audit')
        self.audit_logger.setLevel(logging.INFO)
        
        audit_handler = logging.FileHandler(self.audit_log)
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s | AUDIT | %(message)s'
        ))
        self.audit_logger.addHandler(audit_handler)
    
    def log_signal_received(self, signal_data: Dict[str, Any], source: str = 'webhook'):
        """Log incoming trading signal"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'signal_received',
            'source': source,
            'signal_id': signal_data.get('signal_id', 'unknown'),
            'symbol': signal_data.get('symbol'),
            'action': signal_data.get('action') or signal_data.get('direction'),
            'volume': signal_data.get('volume'),
            'price': signal_data.get('price'),
            'sl': signal_data.get('sl') or signal_data.get('stop_loss'),
            'tp': signal_data.get('tp') or signal_data.get('take_profit')
        }
        
        self.trade_logger.info(f"SIGNAL_RECEIVED | {json.dumps(log_entry)}")
        
        # Audit log
        self.audit_logger.info(
            f"Signal {log_entry['signal_id']} received from {source} | "
            f"{log_entry['symbol']} {log_entry['action']} {log_entry['volume']}"
        )
    
    def log_trade_approved(self, signal_id: str, user_id: int, account: int, 
                          approval_method: str = 'manual'):
        """Log trade approval"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'trade_approved',
            'signal_id': signal_id,
            'user_id': user_id,
            'account': account,
            'approval_method': approval_method
        }
        
        self.trade_logger.info(f"TRADE_APPROVED | {json.dumps(log_entry)}")
        
        # Audit log
        self.audit_logger.info(
            f"Trade {signal_id} approved by user {user_id} for account {account} | "
            f"Method: {approval_method}"
        )
    
    def log_trade_execution(self, trade_request: Dict[str, Any], 
                           result: Dict[str, Any], execution_time: float):
        """Log trade execution details"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'trade_execution',
            'request': {
                'symbol': trade_request.get('symbol'),
                'direction': trade_request.get('direction'),
                'volume': trade_request.get('volume'),
                'account': trade_request.get('account')
            },
            'result': {
                'status': result.get('status'),
                'ticket': result.get('ticket') or result.get('data', {}).get('ticket'),
                'price': result.get('price') or result.get('data', {}).get('price'),
                'message': result.get('message')
            },
            'execution_time_ms': round(execution_time * 1000, 2)
        }
        
        self.trade_logger.info(f"TRADE_EXECUTION | {json.dumps(log_entry)}")
        
        # Audit log
        status = 'SUCCESS' if result.get('status') == 'success' else 'FAILED'
        self.audit_logger.info(
            f"Trade execution {status} | "
            f"Account: {trade_request.get('account')} | "
            f"Ticket: {log_entry['result']['ticket']} | "
            f"Time: {log_entry['execution_time_ms']}ms"
        )
        
        # Log errors separately
        if result.get('status') != 'success':
            self.log_trade_error(
                'execution_failed',
                trade_request,
                result.get('message', 'Unknown error')
            )
    
    def log_trade_error(self, error_type: str, context: Dict[str, Any], 
                       error_message: str, exception: Optional[Exception] = None):
        """Log trade-related errors"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': error_type,
            'context': context,
            'error_message': error_message
        }
        
        if exception:
            log_entry['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        
        self.error_logger.error(f"TRADE_ERROR | {json.dumps(log_entry)}")
        
        # Also log to audit for compliance
        self.audit_logger.error(
            f"ERROR {error_type} | {error_message} | "
            f"Context: {json.dumps(context, default=str)}"
        )
    
    def log_position_update(self, ticket: int, update_type: str, 
                           old_values: Dict[str, Any], new_values: Dict[str, Any]):
        """Log position modifications"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'position_update',
            'ticket': ticket,
            'update_type': update_type,
            'old_values': old_values,
            'new_values': new_values
        }
        
        self.trade_logger.info(f"POSITION_UPDATE | {json.dumps(log_entry)}")
        
        # Audit log
        changes = []
        for key in new_values:
            if key in old_values and old_values[key] != new_values[key]:
                changes.append(f"{key}: {old_values[key]} -> {new_values[key]}")
        
        self.audit_logger.info(
            f"Position {ticket} updated | Type: {update_type} | "
            f"Changes: {', '.join(changes)}"
        )
    
    def log_risk_event(self, event_type: str, details: Dict[str, Any]):
        """Log risk management events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'risk_event',
            'event_type': event_type,
            'details': details
        }
        
        self.trade_logger.warning(f"RISK_EVENT | {json.dumps(log_entry)}")
        
        # Audit log with high priority
        self.audit_logger.warning(
            f"RISK EVENT | Type: {event_type} | "
            f"Details: {json.dumps(details, default=str)}"
        )
    
    def get_trade_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get trading summary for a specific date"""
        if date is None:
            date = datetime.now()
        
        log_file = self.log_dir / f"trades_{date.strftime('%Y%m%d')}.log"
        
        if not log_file.exists():
            return {'error': 'No trades found for this date'}
        
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'total_signals': 0,
            'approved_trades': 0,
            'executed_trades': 0,
            'failed_trades': 0,
            'total_volume': 0.0,
            'symbols_traded': set()
        }
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if 'SIGNAL_RECEIVED' in line:
                        summary['total_signals'] += 1
                    elif 'TRADE_APPROVED' in line:
                        summary['approved_trades'] += 1
                    elif 'TRADE_EXECUTION' in line:
                        try:
                            data = json.loads(line.split('|')[-1].strip())
                            if data['result']['status'] == 'success':
                                summary['executed_trades'] += 1
                                summary['total_volume'] += float(data['request'].get('volume', 0))
                                summary['symbols_traded'].add(data['request'].get('symbol'))
                            else:
                                summary['failed_trades'] += 1
                        except:
                            pass
            
            summary['symbols_traded'] = list(summary['symbols_traded'])
            return summary
            
        except Exception as e:
            logger.error(f"Error reading trade summary: {e}")
            return {'error': str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in self.log_dir.glob("*.log"):
                # Extract date from filename
                try:
                    file_date_str = log_file.stem.split('_')[-1]
                    file_date = datetime.strptime(file_date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        logger.info(f"Deleted old log file: {log_file}")
                        
                except Exception as e:
                    logger.warning(f"Could not process log file {log_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")

# Global trade logger instance
_trade_logger = None

def get_trade_logger() -> TradeLogger:
    """Get or create trade logger instance"""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger