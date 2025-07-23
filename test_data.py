#!/usr/bin/env python3
import importlib.util
import sys

def load_dashboard_module():
    """Load dashboard-to-xe.py module"""
    spec = importlib.util.spec_from_file_location("dashboard_to_xe", "dashboard-to-xe.py")
    dashboard_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dashboard_module)
    return dashboard_module

def main():
    print("🔄 Loading dashboard module...")
    dashboard = load_dashboard_module()
    
    print("🔄 Loading data from GitHub...")
    df_raw = dashboard.load_data_from_github()
    
    print(f"📊 Raw data shape: {df_raw.shape}")
    print(f"📋 Raw columns: {list(df_raw.columns)}")
    
    print("\n🔧 Processing data...")
    df_processed = dashboard.process_dataframe(df_raw)
    
    print(f"📊 Processed data shape: {df_processed.shape}")
    print(f"📋 Processed columns: {list(df_processed.columns)}")
    
    print("\n📄 First 5 rows after processing:")
    print(df_processed.head())
    
    print("\n📊 Column mapping results:")
    for col in df_processed.columns:
        non_null = df_processed[col].notna().sum()
        print(f"  {col}: {non_null}/{len(df_processed)} records")

if __name__ == "__main__":
    main()