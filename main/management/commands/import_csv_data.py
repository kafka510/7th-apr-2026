import os
import pandas as pd
from django.core.management.base import BaseCommand
from main.models import (
    YieldData, BESSData, AOCData, ICEData, ICVSEXVSCURData, MapData, MinamataStringLossData,
    ActualGenerationDailyData, ExpectedBudgetDailyData, BudgetGIIDailyData, ActualGIIDailyData,
    ICApprovedBudgetDailyData, LossCalculationData
)
from datetime import datetime
from django.conf import settings

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_percentage(val):
    """Convert percentage string to float (e.g., '76.43%' -> 76.43)"""
    try:
        if isinstance(val, str) and val.strip().endswith('%'):
            return float(val.strip().replace('%', ''))
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def parse_date(date_str):
    """Parse date string in various formats"""
    try:
        # Handle format like "1/1/2025 0:00"
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None

def import_daily_csv(csv_path, model_class, value_column_name):
    """Generic function to import daily CSV files (wide format)"""
    if not os.path.exists(csv_path):
        return False, f"{os.path.basename(csv_path)} not found"
    
    try:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding='latin-1')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='cp1252')
        
        # Get the date column (first column)
        date_col = df.columns[0]
        
        # Get asset columns (all except date)
        asset_cols = df.columns[1:]
        
        records_created = 0
        
        for _, row in df.iterrows():
            date = parse_date(str(row[date_col]))
            if not date:
                continue
                
            for asset_col in asset_cols:
                asset_code = asset_col.strip()
                value = safe_float(row[asset_col])
                
                if value is not None:
                    # Create or update record
                    obj, created = model_class.objects.get_or_create(
                        date=date,
                        asset_code=asset_code,
                        defaults={value_column_name: value}
                    )
                    if not created:
                        # Update existing record
                        setattr(obj, value_column_name, value)
                        obj.save()
                    
                    records_created += 1
        
        return True, f"Imported {records_created} records into {model_class.__name__}"
    
    except Exception as e:
        return False, f"Error importing {os.path.basename(csv_path)}: {str(e)}"

class Command(BaseCommand):
    help = 'Import all CSVs in django_web_app/data/ into their respective models. Clears existing data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Clearing all data from tables...'))
        YieldData.objects.all().delete()
        BESSData.objects.all().delete()
        AOCData.objects.all().delete()
        ICEData.objects.all().delete()
        ICVSEXVSCURData.objects.all().delete()
        MapData.objects.all().delete()
        MinamataStringLossData.objects.all().delete()
        ActualGenerationDailyData.objects.all().delete()
        ExpectedBudgetDailyData.objects.all().delete()
        BudgetGIIDailyData.objects.all().delete()
        ActualGIIDailyData.objects.all().delete()
        ICApprovedBudgetDailyData.objects.all().delete()
        LossCalculationData.objects.all().delete()

        # 1. YieldData
        yield_path = os.path.join(DATA_DIR, 'yield.csv')
        #print(yield_path)
        if os.path.exists(yield_path):
            try:
                df = pd.read_csv(yield_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(yield_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(yield_path, encoding='cp1252')
            
            for _, row in df.iterrows():
                YieldData.objects.create(
                    month = str(row.get('month', '')),
                    country = str(row.get('country', '')),
                    portfolio = str(row.get('portfolio', '')),
                    assetno = str(row.get('assetno', '')),
                    dc_capacity_mw = safe_float(row.get('dc_capacity_mw')),
                    ic_approved_budget = safe_float(row.get('ic_approved_budget')),
                    expected_budget = safe_float(row.get('expected_budget')),
                    weather_loss_or_gain = safe_float(row.get('weather_loss_or_gain')),
                    grid_curtailment = safe_float(row.get('grid_curtailment')),
                    grid_outage = safe_float(row.get('grid_outage')),
                    operation_budget = safe_float(row.get('operation_budget')),
                    breakdown_loss = safe_float(row.get('breakdown_loss')),
                    unclassified_loss = safe_float(row.get('unclassified_loss')),
                    actual_generation = safe_float(row.get('actual_generation')),
                    string_failure = safe_float(row.get('string failure')),
                    inverter_failure = safe_float(row.get('inverter failure')),
                    mv_failure = safe_float(row.get('mv_failure')),
                    hv_failure = safe_float(row.get('hv_failure')),
                    ac_failure = safe_float(row.get('ac_failure')),
                    
                    expected_pr = safe_float(row.get('expected_pr')),
                    actual_pr = safe_float(row.get('actual_pr')),
                    pr_gap = safe_float(row.get('pr_gap')),
                    pr_gap_observation = str(row.get('pr_gap_observation', '')),
                    pr_gap_action_need_to_taken = str(row.get('pr_gap_action_need_to_taken', '')),
                    revenue_loss = safe_float(row.get('revenue_loss')),
                    revenue_loss_observation = str(row.get('revenue_loss_observation', '')),
                    revenue_loss_action_need_to_taken = str(row.get('revenue_loss_action_need_to_taken', '')),
                    # New fields
                    budgeted_irradiation = safe_float(row.get('budgeted_irradiation')),
                    actual_irradiation = safe_float(row.get('actual_irradiation')),
                    ac_capacity_mw = safe_float(row.get('ac_capacity_mw')),
                    bess_capacity_mwh = safe_float(row.get('bess_capacity_mwh')),
                    bess_generation_mwh = safe_float(row.get('bess_generation_mwh')),
                    # New columns from updated yield.csv
                    ppa_rate = safe_float(row.get('ppa_rate')),
                    ic_approved_budget_dollar = safe_float(row.get('ic_approved_budget_$') or row.get('ic_approved_budget_dollar')),
                    expected_budget_dollar = safe_float(row.get('expected_budget_$') or row.get('expected_budget_dollar')),
                    actual_generation_dollar = safe_float(row.get('actual_generation_$') or row.get('actual_generation_dollar')),
                    operational_budget_dollar = safe_float(row.get('operational_budget_dollar')),
                    revenue_loss_op = safe_float(row.get('revenue_loss_op')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into YieldData'))
        else:
            self.stdout.write(self.style.WARNING('yield.csv not found'))

        # 2. BESSData
        bess_path = os.path.join(DATA_DIR, 'bess.csv')
        if os.path.exists(bess_path):
            try:
                df = pd.read_csv(bess_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(bess_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(bess_path, encoding='cp1252')
           
            for _, row in df.iterrows():
                BESSData.objects.create(
                    date = str(row.get('Date', '')),
                    month = str(row.get('month', '')),
                    country = str(row.get('Country', '')),
                    portfolio = str(row.get('Portfolio', '')),
                    asset_no = str(row.get('Asset No', '')),
                    battery_capacity_mw = safe_float(row.get('Battery Capacity (MW)')),
                    export_energy_kwh = safe_float(row.get('Export Energy (kWh)')),
                    pv_energy_kwh = safe_float(row.get('PV Energy (kWh)')),
                    charge_energy_kwh = safe_float(row.get('Charge Energy (kWh)')),
                    discharge_energy_kwh = safe_float(row.get('Discharge Energy (kWh)')),
                    min_soc = safe_float(row.get('Min SOC ')),
                    max_soc = safe_float(row.get('Max SOC ')),
                    min_ess_temperature = safe_float(row.get('Min ESS Temperature ')),
                    max_ess_temperature = safe_float(row.get('Max ESS Temperature ')),
                    min_ess_humidity = safe_float(row.get('Min ESS Humidity ')),
                    max_ess_humidity = safe_float(row.get('Max ESS Humidity ')),
                    rte = safe_float(row.get('RTE(%)')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into BESSData'))
        else:
            self.stdout.write(self.style.WARNING('bess.csv not found'))

        # 3. AOCData
        aoc_path = os.path.join(DATA_DIR, 'AOC.csv')
        if os.path.exists(aoc_path):
            
            try:
                df = pd.read_csv(aoc_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(aoc_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(aoc_path, encoding='cp1252')
            for _, row in df.iterrows():
                AOCData.objects.create(
                    s_no = str(row.get('s_no', '')),
                    month = str(row.get('month', '')),
                    asset_no = str(row.get('asset_no', '')),
                    country = str(row.get('country', '')),
                    portfolio = str(row.get('portfolio', '')),
                    remarks = str(row.get('remarks', '')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into AOCData'))
        else:
            self.stdout.write(self.style.WARNING('AOC.csv not found'))

        # 4. ICEData (normalized)
        ice_path = os.path.join(DATA_DIR, 'ICE.csv')
        if os.path.exists(ice_path):
            try:
                df = pd.read_csv(ice_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(ice_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(ice_path, encoding='cp1252')
            
            # Process ICE data - skip header rows and total rows
            for idx in range(2, len(df) - 2):  # Skip first 2 rows and last 2 rows
                row = df.iloc[idx]
                month = str(row['Month ']).strip()
                
                # Define portfolio mappings based on actual CSV structure
                portfolios = [
                    ('Japan-Minamata', 'Japan ', ' IC Approved ', ' Expected '),
                    ('Korea-Blackwood', 'Korea- Blackwood', ' IC Approved ', ' Expected '),
                    ('Korea-Iceberg', 'Korea-Iceberg', ' IC Approved ', ' Expected '),
                    ('Korean-Sroof', 'Korean-Sroof', ' IC Approved ', ' Expected '),
                    ('Singapore', 'Singapore', ' IC Approved ', ' Expected '),
                ]
                
                for portfolio, portfolio_col, ic_col, exp_col in portfolios:
                    # Get the actual column names by combining portfolio and metric
                    ic_col_name = portfolio_col + ic_col
                    exp_col_name = portfolio_col + exp_col
                    
                    ic_approved = safe_float(row.get(ic_col_name))
                    expected = safe_float(row.get(exp_col_name))
                    
                    if month and (ic_approved is not None or expected is not None):
                        ICEData.objects.create(
                            month=month,
                            portfolio=portfolio,
                            ic_approved=ic_approved,
                            expected=expected,
                        )
            self.stdout.write(self.style.SUCCESS('Imported ICEData'))
        else:
            self.stdout.write(self.style.WARNING('ICE.csv not found'))

        # 4.5. ICVSEXVSCURData
        icvsexvscur_path = os.path.join(DATA_DIR, 'ICVSEXVSCUR.csv')
        if os.path.exists(icvsexvscur_path):
            try:
                df = pd.read_csv(icvsexvscur_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(icvsexvscur_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(icvsexvscur_path, encoding='cp1252')
            
            for _, row in df.iterrows():
                ICVSEXVSCURData.objects.create(
                    country=str(row.get('Country', '')),
                    portfolio=str(row.get('Portfolio', '')),
                    dc_capacity_mwp=safe_float(row.get('DC Capacity (Mwp)')),
                    month=str(row.get('Month', '')),
                    ic_approved_budget_mwh=safe_float(row.get('IC Approved Budget (MWh)')),
                    expected_budget_mwh=safe_float(row.get('Expected Budget (MWh)')),
                    actual_generation_mwh=safe_float(row.get('Actual Generation (MWh)')),
                    grid_curtailment_budget_mwh=safe_float(row.get('Grid Curtailment Budget (MWh)')),
                    actual_curtailment_mwh=safe_float(row.get('Actual Curtailment (MWh)')),
                    budget_irradiation_kwh_m2=safe_float(row.get('Budget Irradiation (kWh/M2)')),
                    actual_irradiation_kwh_m2=safe_float(row.get('Actual Irradiation (kWh/M2)')),
                    expected_pr_percent=safe_percentage(row.get('Expected PR (%)')),
                    actual_pr_percent=safe_percentage(row.get('Actual PR (%)')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into ICVSEXVSCURData'))
        else:
            self.stdout.write(self.style.WARNING('ICVSEXVSCUR.csv not found'))

        # 5. MapData
        map_path = os.path.join(DATA_DIR, 'map_data.csv')
        if os.path.exists(map_path):
            
            try:
                df = pd.read_csv(map_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(map_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(map_path, encoding='cp1252')
           # print(df)
            for _, row in df.iterrows():
                MapData.objects.create(
                    asset_no = str(row.get('asset_no', '')),
                    country = str(row.get('country', '')),
                    site_name = str(row.get('site_name', '')),
                    portfolio = str(row.get('portfolio', '')),
                    installation_type = str(row.get('installation_type', '')),
                    dc_capacity_mwp = safe_float(row.get('dc_capacity_mwp')),
                    pcs_capacity = str(row.get('pcs_capacity', '')),
                    battery_capacity_mw = str(row.get('battery_capacity_mw', '')),
                    plant_type = str(row.get('plant_type', '')),
                    offtaker = str(row.get('offtaker', '')),
                    cod = str(row.get('cod', '')),
                    latitude = safe_float(row.get('latitude')),
                    longitude = safe_float(row.get('longitude ')),
                )
                
                #print((row.get('longitude')),row.get('latitude'))
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into MapData'))
        else:
            self.stdout.write(self.style.WARNING('map_data.csv not found'))

        # 6. MinamataStringLossData
        minamata_path = os.path.join(DATA_DIR, 'Monthly String Loss.csv')
        if os.path.exists(minamata_path):
            
            try:
                df = pd.read_csv(minamata_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(minamata_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(minamata_path, encoding='cp1252')
            for _, row in df.iterrows():
                MinamataStringLossData.objects.create(
                    month = str(row.get('Month ', '')),
                    no_of_strings_breakdown = safe_int(row.get('No of strings breakdown ')),
                    no_of_strings_modules_damaged = str(row.get('No. of Strings/No. of modules damaged', '')),
                    designed_dc_capacity_mwh = safe_float(row.get('Designed DC capacity (MWh) ')),
                    breakdown_dc_capacity_mwh = safe_float(row.get('Breakdown DC Capacity (MWh) ')),
                    operational_dc_capacity_mwh = safe_float(row.get('Operational DC capacity (MWh) ')),
                    budgeted_gen_mwh = safe_float(row.get('Budgeted Gen (MWh) ')),
                    actual_gen_mwh = safe_float(row.get('Actual Gen (MWh) ')),
                    loss_due_to_string_failure_mwh = safe_float(row.get('Loss due to string failure (MWh) ')),
                    loss_in_jpy = safe_int(row.get('Loss in JPY ')),
                    loss_in_usd = safe_int(row.get('Loss in USD ')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into MinamataStringLossData'))
        else:
            self.stdout.write(self.style.WARNING('Monthly String Loss.csv not found'))
            
        # 7. LossCalculationData
        loss_calculation_path = os.path.join(DATA_DIR, 'Loss Calculation.csv')
        if os.path.exists(loss_calculation_path):
            try:
                df = pd.read_csv(loss_calculation_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(loss_calculation_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(loss_calculation_path, encoding='cp1252')
            
            for _, row in df.iterrows():
                LossCalculationData.objects.create(
                    l=str(row.get('L', '')),
                    month=str(row.get('Month', '')),
                    start_date=str(row.get('Start Dae', '')),
                    start_time=str(row.get('Start Time', '')),
                    end_date=str(row.get('End Date ', '')),
                    end_time=str(row.get('End Time ', '')),
                    asset_no=str(row.get('Asset No ', '')),
                    country=str(row.get('Country ', '')),
                    portfolio=str(row.get('Portfolio', '')),
                    dc_capacity=str(row.get('DC Capacity', '')),
                    site_name=str(row.get('Site Name ', '')),
                    category=str(row.get('Category ', '')),
                    subcategory=str(row.get('Subcatergory', '')),
                    breakdown_equipment=str(row.get('Breakdown Equipment ', '')),
                    bd_description=str(row.get('BD Description ', '')),
                    action_to_be_taken=str(row.get('Action to be taken ', '')),
                    status_of_bd=str(row.get('Status of BD ', '')),
                    breakdown_dc_capacity_kw=safe_float(row.get('Breakdown DC capacity (kW) ')),
                    irradiation_during_breakdown_kwh_m2=safe_float(row.get('irradiation during breakdown (kWh/M2) ')),
                    budget_pr_percent=safe_float(row.get('Budget PR (%) ')),
                    generation_loss_kwh=safe_float(row.get('Generation Loss (kWh) ')),
                    ppa_rate_usd=safe_float(row.get('PPA Rate in USD ')),
                    revenue_loss_usd=safe_float(row.get('Revenue Loss in USD ')),
                    severity=safe_int(row.get('Severity', '')),
                )
            self.stdout.write(self.style.SUCCESS(f'Imported {df.shape[0]} rows into LossCalculationData'))
        else:
            self.stdout.write(self.style.WARNING('Loss Calculation.csv not found'))
            
        # 8. Daily Data Imports
        self.stdout.write(self.style.SUCCESS('Starting daily data imports...'))

        # Actual Generation Daily
        actual_gen_path = os.path.join(DATA_DIR, 'Actual Generation daily.csv')
        success, message = import_daily_csv(actual_gen_path, ActualGenerationDailyData, 'generation_kwh')
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))

        # Expected Budget Daily
        expected_budget_path = os.path.join(DATA_DIR, 'expected budget daily.csv')
        success, message = import_daily_csv(expected_budget_path, ExpectedBudgetDailyData, 'expected_budget_kwh')
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))

        # Budget GII Daily
        budget_gii_path = os.path.join(DATA_DIR, 'BudgetGIIdaily.csv')
        success, message = import_daily_csv(budget_gii_path, BudgetGIIDailyData, 'budget_gii_kwh')
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))

        # Actual GII Daily
        actual_gii_path = os.path.join(DATA_DIR, 'Actual GII Daywise.csv')
        success, message = import_daily_csv(actual_gii_path, ActualGIIDailyData, 'actual_gii_kwh')
        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))

        # 7. ICApprovedBudgetDailyData
        ic_approved_budget_daily_path = os.path.join(DATA_DIR, 'IC_Approved_Budget_Daily.csv')
        if os.path.exists(ic_approved_budget_daily_path):
            try:
                df = pd.read_csv(ic_approved_budget_daily_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(ic_approved_budget_daily_path, encoding='latin-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(ic_approved_budget_daily_path, encoding='cp1252')
            
            # Clear existing data
            ICApprovedBudgetDailyData.objects.all().delete()
            
            records_imported = 0
            for _, row in df.iterrows():
                try:
                    # Parse date
                    date_str = row['Date']
                    date_obj = pd.to_datetime(date_str).date()
                    
                    # Process each asset column (skip the Date column)
                    for col in df.columns:
                        if col != 'Date':
                            asset_code = col
                            value = row[col]
                            
                            if pd.notna(value) and value != '':
                                ICApprovedBudgetDailyData.objects.create(
                                    date=date_obj,
                                    asset_code=asset_code,
                                    ic_approved_budget_kwh=float(value)
                                )
                                records_imported += 1
                
                except Exception as e:
                    print(f"Error processing IC Approved Budget Daily row: {e}")
                    continue
            
            self.stdout.write(self.style.SUCCESS(f'Imported {records_imported} IC Approved Budget Daily records'))
        else:
            self.stdout.write(self.style.WARNING('IC_Approved_Budget_Daily.csv not found'))

        self.stdout.write(self.style.SUCCESS('All imports complete!')) 