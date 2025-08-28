from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models import QuerySet

from ..models import Holding


@dataclass
class PortfolioSummary:
    """Summary metrics for the entire portfolio"""
    total_portfolio_value: Decimal
    total_cost: Decimal  
    total_unrealized_gain_loss: Decimal
    total_unrealized_gain_loss_percent: float
    holdings_count: int


@dataclass
class HoldingWithComposition:
    """Holding enriched with portfolio composition data"""
    holding: Holding
    current_value: Optional[Decimal]
    portfolio_weight_percent: float
    
    @property
    def unrealized_gain_loss(self) -> Optional[Decimal]:
        """Get unrealized gain/loss from the holding"""
        return self.holding.unrealized_gain_loss
    
    @property
    def unrealized_gain_loss_percent(self) -> Optional[float]:
        """Calculate unrealized gain/loss percentage"""
        if self.holding.total_cost and self.holding.total_cost > 0:
            gain_loss = self.holding.unrealized_gain_loss
            if gain_loss is not None:
                return float((gain_loss / self.holding.total_cost) * 100)
        return None


@dataclass
class PortfolioData:
    """Complete portfolio data with holdings and summary"""
    holdings: List[HoldingWithComposition]
    summary: PortfolioSummary


class PortfolioService:
    """Service for portfolio composition and analysis calculations"""
    
    @staticmethod
    def get_user_holdings_queryset(user: User) -> QuerySet[Holding]:
        """Get optimized queryset of user's holdings"""
        return Holding.objects.filter(
            user=user
        ).select_related(
            'security', 
            'security__fundamentals'
        ).order_by('-total_cost')
    
    @staticmethod
    def calculate_portfolio_composition(user: User) -> PortfolioData:
        """
        Calculate complete portfolio composition with percentages and summary.
        
        Args:
            user: User to calculate portfolio for
            
        Returns:
            PortfolioData with holdings and summary metrics
        """
        holdings_queryset = PortfolioService.get_user_holdings_queryset(user)
        
        # Calculate total portfolio value and prepare holdings data
        total_portfolio_value = Decimal('0')
        holdings_with_values = []
        
        for holding in holdings_queryset:
            current_value = holding.current_value
            # Use current market value if available, otherwise use cost basis
            value_for_calculation = current_value if current_value is not None else holding.total_cost
            
            total_portfolio_value += value_for_calculation
            holdings_with_values.append((holding, value_for_calculation))
        
        # Calculate portfolio composition percentages
        holdings_with_composition = []
        for holding, current_value in holdings_with_values:
            if total_portfolio_value > 0:
                weight_percent = float((current_value / total_portfolio_value) * 100)
            else:
                weight_percent = 0.0
                
            holdings_with_composition.append(
                HoldingWithComposition(
                    holding=holding,
                    current_value=current_value,
                    portfolio_weight_percent=round(weight_percent, 2)
                )
            )
        
        # Calculate summary metrics
        summary = PortfolioService._calculate_portfolio_summary(
            holdings_with_composition, 
            total_portfolio_value
        )
        
        return PortfolioData(
            holdings=holdings_with_composition,
            summary=summary
        )
    
    @staticmethod
    def get_portfolio_summary(user: User) -> PortfolioSummary:
        """
        Get portfolio summary metrics only (faster than full composition).
        
        Args:
            user: User to get summary for
            
        Returns:
            PortfolioSummary with total metrics
        """
        portfolio_data = PortfolioService.calculate_portfolio_composition(user)
        return portfolio_data.summary
    
    @staticmethod
    def _calculate_portfolio_summary(
        holdings_with_composition: List[HoldingWithComposition],
        total_portfolio_value: Decimal
    ) -> PortfolioSummary:
        """Calculate summary metrics from holdings data"""
        total_cost = sum(holding.holding.total_cost for holding in holdings_with_composition)
        total_unrealized_gain_loss = sum(
            holding.holding.unrealized_gain_loss or Decimal('0') 
            for holding in holdings_with_composition
        )
        
        # Calculate total unrealized gain/loss percentage
        if total_cost > 0:
            total_unrealized_gain_loss_percent = float(
                (total_unrealized_gain_loss / total_cost) * 100
            )
        else:
            total_unrealized_gain_loss_percent = 0.0
        
        return PortfolioSummary(
            total_portfolio_value=total_portfolio_value,
            total_cost=total_cost,
            total_unrealized_gain_loss=total_unrealized_gain_loss,
            total_unrealized_gain_loss_percent=round(total_unrealized_gain_loss_percent, 2),
            holdings_count=len(holdings_with_composition)
        )