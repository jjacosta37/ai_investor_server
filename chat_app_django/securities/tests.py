from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from .models import Security, SecurityFundamentals, Holding
from .services.portfolio_service import PortfolioService, PortfolioData, PortfolioSummary, HoldingWithComposition


class PortfolioServiceTestCase(TestCase):
    """Test cases for PortfolioService"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test securities
        self.security1 = Security.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            security_type='CS',
            exchange='NASDAQ'
        )
        
        self.security2 = Security.objects.create(
            symbol='MSFT',
            name='Microsoft Corporation',
            security_type='CS', 
            exchange='NASDAQ'
        )
        
        self.security3 = Security.objects.create(
            symbol='SPY',
            name='SPDR S&P 500 ETF',
            security_type='ETF',
            exchange='NYSE'
        )
        
        # Create fundamentals with current prices
        SecurityFundamentals.objects.create(
            security=self.security1,
            current_price=Decimal('175.25')
        )
        
        SecurityFundamentals.objects.create(
            security=self.security2,
            current_price=Decimal('375.80')
        )
        
        SecurityFundamentals.objects.create(
            security=self.security3,
            current_price=Decimal('459.20')
        )
    
    def test_empty_portfolio(self):
        """Test portfolio calculation with no holdings"""
        portfolio_data = PortfolioService.calculate_portfolio_composition(self.user)
        
        self.assertIsInstance(portfolio_data, PortfolioData)
        self.assertEqual(len(portfolio_data.holdings), 0)
        self.assertEqual(portfolio_data.summary.holdings_count, 0)
        self.assertEqual(portfolio_data.summary.total_portfolio_value, Decimal('0'))
        self.assertEqual(portfolio_data.summary.total_cost, Decimal('0'))
        self.assertEqual(portfolio_data.summary.total_unrealized_gain_loss, Decimal('0'))
        self.assertEqual(portfolio_data.summary.total_unrealized_gain_loss_percent, 0.0)
    
    def test_single_holding_portfolio(self):
        """Test portfolio calculation with single holding"""
        # Create single holding
        holding = Holding.objects.create(
            user=self.user,
            security=self.security1,
            quantity=Decimal('100.000000'),
            average_cost=Decimal('150.0000'),
            total_cost=Decimal('15000.0000'),
            first_purchase_date=date(2023, 6, 15)
        )
        
        portfolio_data = PortfolioService.calculate_portfolio_composition(self.user)
        
        # Check portfolio structure
        self.assertEqual(len(portfolio_data.holdings), 1)
        self.assertEqual(portfolio_data.summary.holdings_count, 1)
        
        # Check holding data
        holding_with_comp = portfolio_data.holdings[0]
        self.assertIsInstance(holding_with_comp, HoldingWithComposition)
        self.assertEqual(holding_with_comp.holding.id, holding.id)
        self.assertEqual(holding_with_comp.portfolio_weight_percent, 100.0)
        
        # Check calculated values
        expected_current_value = Decimal('100.000000') * Decimal('175.25')  # 17525.00
        self.assertEqual(holding_with_comp.current_value, expected_current_value)
        
        # Check unrealized gain/loss
        expected_gain_loss = expected_current_value - Decimal('15000.0000')  # 2525.00
        self.assertEqual(holding_with_comp.unrealized_gain_loss, expected_gain_loss)
        
        # Check summary
        self.assertEqual(portfolio_data.summary.total_portfolio_value, expected_current_value)
        self.assertEqual(portfolio_data.summary.total_cost, Decimal('15000.0000'))
        self.assertEqual(portfolio_data.summary.total_unrealized_gain_loss, expected_gain_loss)
    
    def test_multiple_holdings_portfolio(self):
        """Test portfolio calculation with multiple holdings"""
        # Create multiple holdings
        holding1 = Holding.objects.create(
            user=self.user,
            security=self.security1,
            quantity=Decimal('100.000000'),
            average_cost=Decimal('150.0000'),
            total_cost=Decimal('15000.0000'),
            first_purchase_date=date(2023, 6, 15)
        )
        
        holding2 = Holding.objects.create(
            user=self.user,
            security=self.security2,
            quantity=Decimal('15.000000'),
            average_cost=Decimal('320.0000'),
            total_cost=Decimal('4800.0000'),
            first_purchase_date=date(2023, 8, 20)
        )
        
        holding3 = Holding.objects.create(
            user=self.user,
            security=self.security3,
            quantity=Decimal('4.000000'),
            average_cost=Decimal('450.0000'),
            total_cost=Decimal('1800.0000'),
            first_purchase_date=date(2023, 12, 1)
        )
        
        portfolio_data = PortfolioService.calculate_portfolio_composition(self.user)
        
        # Check portfolio structure
        self.assertEqual(len(portfolio_data.holdings), 3)
        self.assertEqual(portfolio_data.summary.holdings_count, 3)
        
        # Calculate expected values
        aapl_value = Decimal('100.000000') * Decimal('175.25')  # 17525.00
        msft_value = Decimal('15.000000') * Decimal('375.80')   # 5637.00
        spy_value = Decimal('4.000000') * Decimal('459.20')     # 1836.80
        total_value = aapl_value + msft_value + spy_value       # 24998.80
        
        # Check holdings are ordered by total_cost (descending)
        holdings_by_cost = sorted(portfolio_data.holdings, key=lambda h: h.holding.total_cost, reverse=True)
        self.assertEqual(holdings_by_cost[0].holding.security.symbol, 'AAPL')  # $15,000
        self.assertEqual(holdings_by_cost[1].holding.security.symbol, 'MSFT')  # $4,800
        self.assertEqual(holdings_by_cost[2].holding.security.symbol, 'SPY')   # $1,800
        
        # Check portfolio percentages sum to 100%
        total_percentage = sum(h.portfolio_weight_percent for h in portfolio_data.holdings)
        self.assertAlmostEqual(total_percentage, 100.0, places=1)
        
        # Check individual percentages
        aapl_holding = next(h for h in portfolio_data.holdings if h.holding.security.symbol == 'AAPL')
        expected_aapl_percent = float((aapl_value / total_value) * 100)
        self.assertAlmostEqual(aapl_holding.portfolio_weight_percent, expected_aapl_percent, places=1)
        
        # Check summary calculations
        self.assertEqual(portfolio_data.summary.total_portfolio_value, total_value)
        self.assertEqual(portfolio_data.summary.total_cost, Decimal('21600.0000'))  # Sum of all total_costs
        
        expected_total_gain_loss = total_value - Decimal('21600.0000')
        self.assertEqual(portfolio_data.summary.total_unrealized_gain_loss, expected_total_gain_loss)
    
    def test_holding_without_current_price(self):
        """Test portfolio calculation when security has no current price"""
        # Create security without fundamentals (no current price)
        security_no_price = Security.objects.create(
            symbol='NOPRICE',
            name='No Price Security',
            security_type='CS',
            exchange='NYSE'
        )
        
        holding = Holding.objects.create(
            user=self.user,
            security=security_no_price,
            quantity=Decimal('50.000000'),
            average_cost=Decimal('100.0000'),
            total_cost=Decimal('5000.0000'),
            first_purchase_date=date(2023, 1, 1)
        )
        
        portfolio_data = PortfolioService.calculate_portfolio_composition(self.user)
        
        # Should use total_cost as current_value when no price available
        holding_with_comp = portfolio_data.holdings[0]
        self.assertEqual(holding_with_comp.current_value, Decimal('5000.0000'))
        self.assertEqual(holding_with_comp.portfolio_weight_percent, 100.0)
        self.assertIsNone(holding_with_comp.unrealized_gain_loss)  # Can't calculate without current price
    
    def test_portfolio_summary_only(self):
        """Test get_portfolio_summary method"""
        # Create a holding
        Holding.objects.create(
            user=self.user,
            security=self.security1,
            quantity=Decimal('100.000000'),
            average_cost=Decimal('150.0000'),
            total_cost=Decimal('15000.0000'),
            first_purchase_date=date(2023, 6, 15)
        )
        
        summary = PortfolioService.get_portfolio_summary(self.user)
        
        self.assertIsInstance(summary, PortfolioSummary)
        self.assertEqual(summary.holdings_count, 1)
        self.assertTrue(summary.total_portfolio_value > 0)
        self.assertEqual(summary.total_cost, Decimal('15000.0000'))
    
    def test_user_isolation(self):
        """Test that portfolio calculations are isolated per user"""
        # Create another user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Create holdings for both users
        Holding.objects.create(
            user=self.user,
            security=self.security1,
            quantity=Decimal('100.000000'),
            average_cost=Decimal('150.0000'),
            total_cost=Decimal('15000.0000'),
            first_purchase_date=date(2023, 6, 15)
        )
        
        Holding.objects.create(
            user=user2,
            security=self.security2,
            quantity=Decimal('50.000000'),
            average_cost=Decimal('300.0000'),
            total_cost=Decimal('15000.0000'),
            first_purchase_date=date(2023, 6, 15)
        )
        
        # Check user1 portfolio
        portfolio1 = PortfolioService.calculate_portfolio_composition(self.user)
        self.assertEqual(len(portfolio1.holdings), 1)
        self.assertEqual(portfolio1.holdings[0].holding.security.symbol, 'AAPL')
        
        # Check user2 portfolio
        portfolio2 = PortfolioService.calculate_portfolio_composition(user2)
        self.assertEqual(len(portfolio2.holdings), 1)
        self.assertEqual(portfolio2.holdings[0].holding.security.symbol, 'MSFT')
