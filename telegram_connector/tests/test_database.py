"""
Test suite for database functionality
"""
import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database

class TestDatabase(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        self.db = Database(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        self.db.close()
        shutil.rmtree(self.test_dir)
    
    def test_user_registration(self):
        """Test user registration"""
        # Register a new user
        success = self.db.register_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            mt4_account=12345
        )
        
        self.assertTrue(success)
        
        # Get user
        user = self.db.get_user(123456789)
        self.assertIsNotNone(user)
        self.assertEqual(user['telegram_id'], 123456789)
        self.assertEqual(user['username'], 'testuser')
        self.assertEqual(user['mt4_account'], 12345)
    
    def test_duplicate_registration(self):
        """Test duplicate user registration updates existing"""
        # Register user
        self.db.register_user(123456789, "user1", "First", "User")
        
        # Register again with different data
        success = self.db.register_user(123456789, "user2", "Second", "User")
        self.assertTrue(success)
        
        # Should update existing user
        user = self.db.get_user(123456789)
        self.assertEqual(user['username'], 'user2')
        self.assertEqual(user['first_name'], 'Second')
    
    def test_user_settings(self):
        """Test user settings management"""
        user_id = 123456789
        
        # Register user
        self.db.register_user(user_id)
        
        # Get default settings
        settings = self.db.get_user_settings(user_id)
        self.assertEqual(settings['risk_percent'], 1.0)
        self.assertEqual(settings['default_lot_size'], 0.01)
        self.assertFalse(settings['auto_trade'])
        self.assertTrue(settings['notifications'])
    
    def test_update_settings(self):
        """Test updating user settings"""
        user_id = 123456789
        self.db.register_user(user_id)
        
        # Update settings
        new_settings = {
            'risk_percent': 2.5,
            'default_lot_size': 0.1,
            'auto_trade': True,
            'notifications': False
        }
        
        success = self.db.update_user_settings(user_id, new_settings)
        self.assertTrue(success)
        
        # Verify updates
        settings = self.db.get_user_settings(user_id)
        self.assertEqual(settings['risk_percent'], 2.5)
        self.assertEqual(settings['default_lot_size'], 0.1)
        self.assertTrue(settings['auto_trade'])
        self.assertFalse(settings['notifications'])
    
    def test_signal_history(self):
        """Test signal history tracking"""
        user_id = 123456789
        self.db.register_user(user_id)
        
        # Add signal
        signal_data = {
            'signal_id': 'test_signal_123',
            'telegram_id': user_id,
            'mt4_account': 12345,
            'symbol': 'EURUSD',
            'action': 'BUY',
            'volume': 0.1,
            'price': 1.1234,
            'sl': 1.1200,
            'tp': 1.1300,
            'status': 'pending'
        }
        
        success = self.db.add_signal_history(signal_data)
        self.assertTrue(success)
        
        # Get user signals
        signals = self.db.get_user_signals(user_id)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['signal_id'], 'test_signal_123')
        self.assertEqual(signals[0]['symbol'], 'EURUSD')
    
    def test_update_signal_status(self):
        """Test updating signal status"""
        user_id = 123456789
        signal_id = 'test_signal_456'
        
        self.db.register_user(user_id)
        
        # Add signal
        self.db.add_signal_history({
            'signal_id': signal_id,
            'telegram_id': user_id,
            'symbol': 'GBPUSD',
            'action': 'SELL',
            'volume': 0.2,
            'status': 'pending'
        })
        
        # Update status
        success = self.db.update_signal_status(
            signal_id, 
            'executed', 
            ticket=12345,
            executed_at=datetime.now()
        )
        self.assertTrue(success)
        
        # Verify update
        signals = self.db.get_user_signals(user_id)
        self.assertEqual(signals[0]['status'], 'executed')
        self.assertEqual(signals[0]['ticket'], 12345)
        self.assertIsNotNone(signals[0]['executed_at'])
    
    def test_user_stats(self):
        """Test user statistics calculation"""
        user_id = 123456789
        self.db.register_user(user_id)
        
        # Add multiple signals
        signals = [
            {'signal_id': 's1', 'status': 'executed', 'profit': 50},
            {'signal_id': 's2', 'status': 'executed', 'profit': -30},
            {'signal_id': 's3', 'status': 'executed', 'profit': 100},
            {'signal_id': 's4', 'status': 'rejected', 'profit': 0},
        ]
        
        for i, signal in enumerate(signals):
            signal.update({
                'telegram_id': user_id,
                'symbol': 'EURUSD',
                'action': 'BUY',
                'volume': 0.1
            })
            self.db.add_signal_history(signal)
            
            # Update profit for executed trades
            if signal['status'] == 'executed':
                self.db.conn.execute(
                    "UPDATE signal_history SET profit = ? WHERE signal_id = ?",
                    (signal['profit'], signal['signal_id'])
                )
        self.db.conn.commit()
        
        # Get stats
        stats = self.db.get_user_stats(user_id)
        
        self.assertEqual(stats['total_trades'], 4)
        self.assertEqual(stats['executed_trades'], 3)
        self.assertEqual(stats['rejected_trades'], 1)
        self.assertEqual(stats['total_profit'], 150)  # 50 + 100
        self.assertEqual(stats['total_loss'], -30)
        self.assertAlmostEqual(stats['win_rate'], 66.67, places=1)  # 2/3 winning trades
    
    def test_nonexistent_user(self):
        """Test handling of nonexistent users"""
        user = self.db.get_user(999999999)
        self.assertIsNone(user)
        
        settings = self.db.get_user_settings(999999999)
        # Should return defaults
        self.assertEqual(settings['risk_percent'], 1.0)
        
        signals = self.db.get_user_signals(999999999)
        self.assertEqual(len(signals), 0)

if __name__ == '__main__':
    unittest.main()