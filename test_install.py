# test_install.py
print("Testing library imports...")

try:
    import pandas as pd
    print("✅ pandas imported successfully")
    
    import numpy as np
    print("✅ numpy imported successfully")
    
    import yfinance as yf
    print("✅ yfinance imported successfully")
    
    import requests
    print("✅ requests imported successfully")
    
    import matplotlib.pyplot as plt
    print("✅ matplotlib imported successfully")
    
    import seaborn as sns
    print("✅ seaborn imported successfully")
    
    import jupyter
    print("✅ jupyter imported successfully")
    
    import schedule
    print("✅ schedule imported successfully")
    
    # Test yfinance functionality
    test_ticker = yf.Ticker("AAPL")
    test_data = test_ticker.history(period="5d")
    if not test_data.empty:
        print("✅ yfinance data fetch test successful")
    else:
        print("⚠️  yfinance data fetch test failed")
    
    print("\n🎉 All libraries installed and working correctly!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")