/**
 * Template Downloader Utility
 */

export type TemplateType =
  | 'yield'
  | 'bess'
  | 'bess_v1'
  | 'actual_generation_daily'
  | 'expected_budget_daily'
  | 'map'
  | 'aoc'
  | 'ice'
  | 'icvsexvscur'
  | 'minamata'
  | 'ic_approved_budget_daily'
  | 'loss_calculation';

export function downloadTemplate(dataType: TemplateType): void {
  // Create sample data based on data type
  let csvContent = '';
  let filename = '';

  switch (dataType) {
    case 'yield':
      csvContent =
        'month,country,portfolio,assetno,dc_capacity_mw,ic_approved_budget,expected_budget,weather_loss_or_gain,weather_corrected_budget,grid_curtailment,actual_curtailment,grid_outage,grid_loss,scheduled_outage_loss,operation_budget,string failure,inverter failure,ac_failure,breakdown_loss,unclassified_loss,unclassified_loss_%,ac_capacity_mw,bess_capacity_mwh,bess_generation_mwh,budgeted_irradiation,actual_irradiation,expected_pr,actual_pr,pr_gap,pr_gap_observation,pr_gap_action_need_to_taken,revenue_loss,revenue_loss_observation,revenue_loss_action_need_to_taken,ppa_rate,ic_approved_budget_$,expected_budget_$,actual_generation_$,operational_budget_dollar,revenue_loss_op\n2024-01,JP,Portfolio A,JP-MINA,10.5,1000.0,950.0,5.2,955.2,2.1,0.0,0.5,0.3,0.0,10.0,0.8,0.3,0.1,1.5,3.2,2.5,10.0,2.5,200.0,4.5,4.3,85.5,82.3,3.2,Low PR due to weather,Monitor weather patterns,15000.0,Revenue loss observed,Review PPA terms,0.15,150.0,142.5,138.0,150.0,-12.0\n2024-01,KR,Portfolio B,KR_BW_01,15.2,1500.0,1450.0,6.1,1456.1,2.5,0.0,0.8,0.5,0.0,12.0,1.2,0.5,0.2,2.0,4.5,3.2,15.0,3.0,250.0,5.2,5.0,86.2,83.1,3.1,Minor PR gap,Check inverter performance,18000.0,Review revenue impact,Optimize operations,0.12,180.0,174.0,170.4,175.0,-5.0';
      filename = 'yield_data_template.csv';
      break;
    case 'bess':
      csvContent =
        'date,month,country,portfolio,asset_no,battery_capacity_mw,export_energy_kwh,charge_energy_kwh\n2024-01-15,2024-01,JP,Portfolio A,JP-MINA,5.0,1200.5,1100.2';
      filename = 'bess_data_template.csv';
      break;
    case 'bess_v1':
      csvContent =
        'month,country,portfolio,asset_no,battery_capacity_mwh,actual_pv_energy_kwh,actual_export_energy_kwh,actual_charge_energy_kwh,actual_discharge_energy,actual_pv_grid_kwh,actual_system_losses,min_soc,max_soc,min_ess_temp,max_ess_temp,actual_avg_rte,actual_cuf,actual_no_of_cycles,budget_pv_energy_kwh,budget_export_energy_kwh,budget_charge_energy_kwh,budget_discharge_energy,budget_pv_grid_kwh,budget_system_losses,budget_cuf,budget_no_of_cycles,budget_grid_import_kwh,actual_grid_import_kwh,budget_avg_rte\n2025-01,Korea,Blackwood,KR_BW_18,1.4976,39748,38327,19371,17950,20377,-1421,2%,91%,16.5,22.3,93.66813038,43.44%,31,35470.69409,32186.61328,26105.57088,22821.49006,9365.123218,-3284.080816,56.49%,31,0,0,95\n2025-01,Korea,Blackwood,KR_BW_36,0.832,21295.8,20643.8,11770,11118,9525.8,-652,1%,90%,15.7,22.9,95.95369453,48.43%,31,20386.51023,18309.03893,16514.08031,14436.60901,3872.429926,-2077.471303,64.34%,31,0,0,95';
      filename = 'bess_v1_data_template.csv';
      break;
    case 'actual_generation_daily':
      csvContent = 'date,asset_code,generation_kwh\n2024-01-15,JP-MINA,2500.5\n2024-01-15,KR_BW_01,3200.8';
      filename = 'actual_generation_daily_template.csv';
      break;
    case 'expected_budget_daily':
      csvContent = 'date,asset_code,expected_budget_kwh\n2024-01-15,JP-MINA,2400.0\n2024-01-15,KR_BW_01,3000.0';
      filename = 'expected_budget_daily_template.csv';
      break;
    case 'map':
      csvContent =
        'asset_no,country,site_name,portfolio,dc_capacity_mwp,latitude,longitude\nJP-MINA,JP,Minamata Solar Plant,Portfolio A,10.5,32.2094,130.4017';
      filename = 'map_data_template.csv';
      break;
    case 'aoc':
      csvContent = 's_no,month,asset_no,country,portfolio,issue_description,status\n1,2024-01,JP-MINA,JP,Portfolio A,Sample issue,Open';
      filename = 'aoc_data_template.csv';
      break;
    case 'ice':
      csvContent =
        'month,portfolio,ic_approved,expected\n2024-01,Portfolio A,1000.0,950.0\n2024-01,Portfolio B,1500.0,1450.0';
      filename = 'ice_data_template.csv';
      break;
    case 'icvsexvscur':
      csvContent =
        'Country,Portfolio,DC Capacity (Mwp),Month,IC Approved Budget (MWh),Expected Budget (MWh),Actual Generation (MWh),Grid Curtailment Budget (MWh),Actual Curtailment (MWh),Budget Irradiation (kWh/M2),Actual Irradiation (kWh/M2),Expected PR (%),Actual PR (%)\nJapan,JP Minamata,28.25,25-Jan,2072.6,2018.5,1554.2,251.8,515.65,93.5,100.84,76.43%,54.57%\nKorea,Korea-Blackwood,64.13,25-Jan,5863.3,5635.4,5332.7,0,0,4983,5468.9,80.49%,66.80%';
      filename = 'icvsexvscur_data_template.csv';
      break;
    case 'minamata':
      csvContent = 'month,string_loss_percentage,damage_description\n2024-01,2.5,Minor damage from typhoon';
      filename = 'minamata_data_template.csv';
      break;
    case 'ic_approved_budget_daily':
      csvContent = 'date,asset_code,ic_approved_budget_kwh\n2024-01-15,JP-MINA,2400.0\n2024-01-15,KR_BW_01,3000.0';
      filename = 'ic_approved_budget_daily_template.csv';
      break;
    case 'loss_calculation':
      csvContent =
        'L,Month,Start Date,Start Time,End Date,End Time,Asset No,Country,Portfolio,DC Capacity,Site Name,Category,Subcategory,Breakdown Equipment,BD Description,Action to be taken,Status of BD,Breakdown DC capacity (kW),irradiation during breakdown (kWh/M2),Budget PR (%),Generation Loss (kWh),PPA Rate in USD,Revenue Loss in USD,Severity\n8,25-Jan,28-Jan-25,6:30,31-Jan-25,18:00,KR_BW_06,Korea,Korea-Blackwood,996.4,Narae Solar Power,Plant,Inverter Failure,All Inverters,Inverter production issue. Information not received from PEK team,Response is pending from PEK Team,Closed,996.4,13.25,0.859570552,-11661.59,0.078421904,-914.5240919,0';
      filename = 'loss_calculation_template.csv';
      break;
    default:
      alert('Template not available for this data type');
      return;
  }

  // Create and download the file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

