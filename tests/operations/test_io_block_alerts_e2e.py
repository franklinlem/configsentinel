"""Synthetic validation: I/O block, collection delay, queue saturation and monitor assessment."""
import unittest
from pathlib import Path
import runpy
from unittest.mock import patch

m = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/monitor-agent-alerts.py'))
AGENT_ID = '05575808-55d7-4401-98c7-496ebda4db23'

class IOBlockAndAlertsTest(unittest.TestCase):
    def test_delayed_collection_triggers_monitor_down(self):
        """When I/O block stalls collection, observed_at ages while seen_at stays fresh, triggering collection_delayed."""
        mock_alerts = [
            {'id': AGENT_ID, 'source': 'agent', 'kind': 'collection_delayed', 'severity': 'warning'}
        ]
        config = {'agent_ids': [AGENT_ID], 'email': 'test@example.com', 'password': 'test'}
        
        def fake_request(opener, path, body=None, csrf=''):
            if path == '/auth/login': return {'csrf_token': 'fake'}
            if path == '/auth/logout': return {'ok': True}
            if path == '/servers': return {'items': [{'agent_id': AGENT_ID}]}
            return {'items': mock_alerts}

        with patch.dict(m['assess'].__globals__, {'request': fake_request}):
            result = m['assess'](config, opener=None)
            self.assertEqual(result['status'], 'down')
            self.assertEqual(result['reason'], 'agent_alert')

    def test_queue_saturation_triggers_monitor_down(self):
        """When queue reaches 80% capacity (e.g. during persistent network cut), queue_high triggers down."""
        mock_alerts = [
            {'id': AGENT_ID, 'source': 'agent', 'kind': 'queue_high', 'severity': 'warning'}
        ]
        config = {'agent_ids': [AGENT_ID], 'email': 'test@example.com', 'password': 'test'}
        
        def fake_request(opener, path, body=None, csrf=''):
            if path == '/auth/login': return {'csrf_token': 'fake'}
            if path == '/auth/logout': return {'ok': True}
            if path == '/servers': return {'items': [{'agent_id': AGENT_ID}]}
            return {'items': mock_alerts}

        with patch.dict(m['assess'].__globals__, {'request': fake_request}):
            result = m['assess'](config, opener=None)
            self.assertEqual(result['status'], 'down')
            self.assertEqual(result['reason'], 'agent_alert')

    def test_agent_offline_triggers_monitor_down(self):
        """When agent host is disconnected, agent_offline triggers down."""
        mock_alerts = [
            {'id': AGENT_ID, 'source': 'agent', 'kind': 'agent_offline', 'severity': 'warning'}
        ]
        config = {'agent_ids': [AGENT_ID], 'email': 'test@example.com', 'password': 'test'}
        
        def fake_request(opener, path, body=None, csrf=''):
            if path == '/auth/login': return {'csrf_token': 'fake'}
            if path == '/auth/logout': return {'ok': True}
            if path == '/servers': return {'items': [{'agent_id': AGENT_ID}]}
            return {'items': mock_alerts}

        with patch.dict(m['assess'].__globals__, {'request': fake_request}):
            result = m['assess'](config, opener=None)
            self.assertEqual(result['status'], 'down')
            self.assertEqual(result['reason'], 'agent_alert')

    def test_healthy_recovery_returns_up(self):
        """When I/O block clears and collection resumes, monitor returns to up."""
        config = {'agent_ids': [AGENT_ID], 'email': 'test@example.com', 'password': 'test'}
        
        def fake_request(opener, path, body=None, csrf=''):
            if path == '/auth/login': return {'csrf_token': 'fake'}
            if path == '/auth/logout': return {'ok': True}
            if path == '/servers': return {'items': [{'agent_id': AGENT_ID}]}
            return {'items': []}

        with patch.dict(m['assess'].__globals__, {'request': fake_request}):
            result = m['assess'](config, opener=None)
            self.assertEqual(result['status'], 'up')
            self.assertEqual(result['reason'], 'agents_healthy')

if __name__ == '__main__':
    unittest.main()
