# Small-Cap Growth Stock Trading System - Agent Build Instructions

## System Overview
Build a comprehensive Python-based trading analysis and screening system for small-cap growth stocks using documented successful individual investor strategies. The system should auto-discover stocks, backtest multiple strategies, manage risk, and provide actionable trading signals.

## Work Methodology
Read the below and think very hard to properly understand the requirements, the expected outcome and come up with an implementation plan. create a project_plan.md file at the root of the project where you outline this plan and split it into SMART tasks and sub tasks. each time you implement a task or a sub task, review the plan and update it if necessary. cross out any tasks / sub tasks you imeplement to keep track of the implementation progress. 
Do not constantly ask me for approval to run scripts, i am hereby granting you my explicit approval. only stop and ask me if you need clarifications
 
 ## Core Requirements

### Target Universe & Strategy
- **Stock Universe**: Small-cap stocks ($50M-$2B market cap) with growth potential
- **Primary Sectors**: Biotech, Information Technology, Solar Energy, Energy (flexible for other opportunities)
- **Strategies to Implement**:
  1. Dan Zanger Model (30% weight): Cup-and-handle patterns, breakouts with volume confirmation
  2. CAN SLIM Model (25% weight): William O'Neil's systematic approach with earnings growth, relative strength
  3. Trend Following Model (25% weight): Ed Seykota-style EMA crossovers with ATR-based stops
  4. Livermore Breakout Model (20% weight): Consolidation breakouts with volume confirmation

### Data Sources (Free/Affordable)
- Yahoo Finance (primary): Daily OHLCV data, basic fundamentals
- Alpha Vantage API: Earnings data, economic indicators
- Google Finance: Backup price data
- FRED Economic Data: Macroeconomic indicators
- SEC EDGAR: Fundamental data (if feasible)

### Risk Management Parameters
- **Position Sizing**: Start equal-weight, migrate to conviction-weighted
- **Individual Trade Stops**: 7-8% maximum loss per position
- **Portfolio Drawdown**: 15-20% maximum peak-to-trough
- **Portfolio Size**: 10-20 positions (flexible based on opportunities)
- **Sector Limits**: Biotech 35%, IT 40%, Energy 30%, Others 25%

### Liquidity Requirements
- Minimum daily volume: $500K
- Maximum spread: <3%
- Minimum float: >10M shares outstanding

### Backtesting Specifications
- **Time Horizon**: 5+ years of historical data
- **Approach**: Static parameters initially (migrate to walk-forward later)
- **Transaction Costs**: Include realistic costs (0.1-0.3% per trade)
- **Testing Method**: Individual strategies first, then combined approach
- **Performance Target**: 20%+ annual returns with controlled risk

### Operational Workflow
- **Scan Frequency**: Weekly (Sunday evenings)
- **Position Tracking**: Automatic tracking of paper trading positions
- **Alerts**: Email notifications for new signals and exit alerts
- **Reporting**: Weekly performance reports with attribution analysis

### Technical Infrastructure
- **Data Storage**: Start with CSV files, easy migration path to SQLite
- **Interface**: Jupyter Notebook environment for analysis and visualization
- **Email Integration**: Configurable SMTP for alerts and reports
- **Broker Integration**: Manual execution (Webull doesn't have retail API)
- **Paper Trading**: Internal tracking system

## Detailed Strategy Implementations

### 1. Dan Zanger Cup-and-Handle Model
```python
# Core Logic Requirements:
- Identify cup formations: 12-35% decline followed by 85%+ recovery
- Handle formation: 5-15% shallow pullback from cup recovery
- Breakout criteria: 2%+ above resistance with 1.5x average volume
- Risk management: 8% stop loss below handle low
- Target: 25% profit target based on pattern depth
```

### 2. CAN SLIM Model
```python
# Scoring Components:
- Current/Annual Earnings: >25% growth (25 points)
- Relative Strength: 80+ vs S&P 500 (25 points)  
- Price Pattern: Within 15% of 52-week high (25 points)
- Institutional Buying: Volume increase >20% (25 points)
- Minimum Score: 75/100 for buy signal
- Risk Management: 8% stop loss, 20% profit target
```

### 3. Trend Following Model
```python
# EMA System:
- Fast EMA: 10-day
- Slow EMA: 30-day
- Entry: Fast EMA crosses above Slow EMA + price above Fast EMA
- Exit: Fast EMA crosses below Slow EMA
- Stop Loss: 2x ATR below entry
- Target: 3x ATR above entry (1:3 risk/reward)
```

### 4. Livermore Breakout Model
```python
# Consolidation Breakout:
- Identify 20+ day consolidation periods
- Range tightness: <15% high-to-low range
- Breakout: 2%+ above range with 1.3x volume
- Risk Management: Stop just below consolidation low
- Target: 2x consolidation range size
```

### Signal Combination Logic
- **Individual View**: Show each strategy's signals separately
- **Combined View**: Aggregate signals with confidence scores
- **Multiple Strategy Signals**: Same stock from multiple strategies = higher confidence (not larger position)
- **Dynamic Weighting**: Adjust strategy weights based on trailing 6-month performance

## Stock Discovery System
```python
# Auto-Discovery Requirements:
1. Screen all US stocks for market cap $50M-$2B
2. Filter by daily volume >$500K
3. Filter by sectors: Biotech, IT, Energy, Solar + others
4. Apply liquidity filters (spread <3%, float >10M)
5. Create universe of ~500-1500 stocks
6. Update universe monthly
```

## System Architecture

### Core Modules Required:
1. **DataProvider**: Multi-source data fetching and caching
2. **StockScreener**: Universe discovery and filtering
3. **StrategyEngine**: Individual strategy implementations
4. **BacktestEngine**: Historical performance analysis
5. **RiskManager**: Position sizing and risk controls
6. **PortfolioTracker**: Paper trading position management
7. **AlertSystem**: Email notifications and reporting
8. **Dashboard**: Jupyter-based analysis interface

### File Structure:
```
trading_system/
├── config/
│   ├── settings.json
│   └── email_config.json
├── data/
│   ├── universe/
│   ├── prices/
│   └── signals/
├── strategies/
│   ├── zanger_model.py
│   ├── canslim_model.py
│   ├── trend_following.py
│   └── livermore_breakouts.py
├── core/
│   ├── data_provider.py
│   ├── backtest_engine.py
│   ├── risk_manager.py
│   └── portfolio_tracker.py
├── notebooks/
│   ├── daily_analysis.ipynb
│   └── strategy_research.ipynb
└── main.py
```

## Task Management System

Create and maintain a comprehensive task list that you check off as you complete each component. After each major completion, review and update the task list with any new requirements discovered during implementation.

### Master Task List Template:
```markdown
## Phase 1: Core Infrastructure
- [ ] Set up project structure and configuration system
- [ ] Implement DataProvider class with Yahoo Finance integration
- [ ] Add Alpha Vantage integration for earnings data
- [ ] Create stock universe discovery system
- [ ] Implement data caching (CSV-based)

## Phase 2: Strategy Implementation
- [ ] Build Dan Zanger cup-and-handle detection
- [ ] Implement CAN SLIM scoring system
- [ ] Create trend following EMA system
- [ ] Build Livermore breakout detection
- [ ] Add signal confidence scoring

## Phase 3: Risk Management & Portfolio
- [ ] Implement position sizing algorithms
- [ ] Build drawdown monitoring
- [ ] Add sector concentration limits
- [ ] Create portfolio tracking system
- [ ] Implement paper trading functionality

## Phase 4: Backtesting & Analysis
- [ ] Build backtesting engine with transaction costs
- [ ] Implement individual strategy testing
- [ ] Create combined strategy backtesting
- [ ] Add performance attribution analysis
- [ ] Build comparison and reporting tools

## Phase 5: Automation & Alerts
- [ ] Implement email alert system
- [ ] Create weekly scanning automation
- [ ] Build performance reporting
- [ ] Add exit signal monitoring
- [ ] Create dashboard visualizations

## Phase 6: Integration & Testing
- [ ] Build Jupyter notebook interface
- [ ] Implement configuration management
- [ ] Add error handling and logging
- [ ] Create user documentation
- [ ] Perform end-to-end system testing

## Ongoing Tasks:
- [ ] Review and update task list after each phase
- [ ] Test individual components as built
- [ ] Validate against requirements
- [ ] Document any deviations or improvements
```

## Specific Implementation Guidelines

### Data Handling:
- Cache all data locally to minimize API calls
- Implement robust error handling for data failures
- Use pandas throughout for data manipulation
- Store signals and positions in structured format

### Performance Requirements:
- Weekly scans should complete within 30 minutes
- Support universe of 500-1500 stocks
- Maintain 5+ years of historical data
- Generate alerts within 1 hour of scan completion

### Configuration System:
```json
{
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "recipient": "alerts@yourmail.com"
  },
  "risk_management": {
    "max_positions": 20,
    "individual_stop": 0.08,
    "portfolio_stop": 0.20,
    "sector_limits": {
      "biotech": 0.35,
      "technology": 0.40,
      "energy": 0.30,
      "other": 0.25
    }
  },
  "strategy_weights": {
    "zanger": 0.30,
    "canslim": 0.25,
    "trend_following": 0.25,
    "livermore": 0.20
  }
}
```

### Error Handling Requirements:
- Graceful handling of missing data
- Retry logic for API failures
- Comprehensive logging of all operations
- Email alerts for system failures

## Deliverables Expected:
1. Complete Python system with all modules
2. Jupyter notebooks for analysis and monitoring
3. Configuration files for easy customization
4. Documentation for setup and usage
5. Sample backtest results and analysis
6. Task completion checklist with status

## Success Criteria:
- System successfully discovers and screens small-cap universe
- All four strategies implemented and generating signals
- Backtesting shows historical performance metrics
- Risk management properly constrains positions and drawdown
- Weekly automation runs successfully
- Email alerts function correctly
- Paper trading tracking works accurately

## Technical Notes:
- Use Python 3.8+ with standard data science libraries
- Ensure all code is well-commented and modular
- Build in easy migration path from CSV to SQLite
- Make system easily configurable without code changes
- Include comprehensive error handling and logging

Build this system incrementally, testing each component thoroughly before moving to the next. Update the task list after each major milestone and provide status updates on completion.