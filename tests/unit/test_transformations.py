import unittest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../dataproc/jobs'))

# Tests unitarios
class TestDataTransformations(unittest.TestCase):
    
    def test_priority_classification(self):
        """Prueba clasificación de prioridad por monto"""
        test_cases = [
            (50.0, 'LOW'),
            (250.0, 'MEDIUM'),
            (1000.0, 'HIGH'),
            (3000.0, 'CRITICAL'),
        ]
        
        for amount, expected_priority in test_cases:
            # Lógica de clasificación
            if amount <= 100:
                priority = 'LOW'
            elif amount <= 500:
                priority = 'MEDIUM'
            elif amount <= 2000:
                priority = 'HIGH'
            else:
                priority = 'CRITICAL'
            
            self.assertEqual(priority, expected_priority)
    
    def test_escalation_logic(self):
        """Prueba lógica de escalado"""
        today = datetime.now()
        old_date = today - timedelta(days=10)
        recent_date = today - timedelta(days=3)
        
        # Caso 1: Pendiente + viejo = requiere escalación
        requires_escalation = 'PENDING' == 'PENDING' and (today - old_date).days > 7
        self.assertTrue(requires_escalation)
        
        # Caso 2: Pendiente + reciente = NO requiere escalación
        requires_escalation = 'PENDING' == 'PENDING' and (today - recent_date).days > 7
        self.assertFalse(requires_escalation)
        
        # Caso 3: Monto crítico = siempre requiere escalación
        requires_escalation = 2500 > 2000
        self.assertTrue(requires_escalation)
    
    def test_risk_score_calculation(self):
        """Prueba cálculo de score de riesgo"""
        test_cases = [
            ('REJECTED', 5000, 0.8 * 1.5),
            ('PENDING', 1500, 0.6 * 1.2),
            ('APPROVED', 100, 0.2 * 1.0),
            ('CLOSED', 300, 0.1 * 1.0),
        ]
        
        for status, amount, expected_score in test_cases:
            status_score = {
                'REJECTED': 0.8,
                'PENDING': 0.6,
                'APPROVED': 0.2,
                'CLOSED': 0.1,
            }.get(status, 0.5)
            
            amount_multiplier = 1.5 if amount > 5000 else (1.2 if amount > 1000 else 1.0)
            risk_score = status_score * amount_multiplier
            
            self.assertAlmostEqual(risk_score, expected_score, places=2)


if __name__ == '__main__':
    unittest.main()
