# venv: ewf-tech

# requirements: numpy==1.24.4, pandas==1.5.3, pytz==2025.2, astral==3.2, scipy==1.13.1, openpyxl==3.1.5

"""
Bezetting berekeningsmodule voor EWF Tech Simulator.

Deze module berekent bezettingspercentages en afgeleide luchtstroomsnelheden
op basis van inputdata en bezettingsschema's. Incl. foutafhandeling
en bestandsbeschermingsmechanismen.
"""

import numpy as np
import pandas as pd
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from ewf_utils import dm3_m_3, air_flow_office_set__dm3_s_1_p_1, flow_modulation_depth__0, fan_modulation_depth__0, eta_fan_min__W0, eta_fan_max__W0
from exceptions import create_file_not_found_error, create_permission_error, create_data_validation_error, create_configuration_error, create_processing_error

# Calculation occupancy and derived air flow
def calculate_occupancy(jaar: int, pad: str, df: pd.DataFrame, occupancy_mean__p: float = 165) -> pd.DataFrame:
    """Bereken bezetting en afgeleide luchtstroom.

    Args:
        jaar: Jaar voor tijdsberekening.
        pad: Pad naar het bezettings CSV bestand.
        df: Input DataFrame met tijd index.
        occupancy_mean__p: Gemiddelde bezetting in personen, standaard 165.

    Returns:
        DataFrame met toegevoegde kolommen:
        - occupancy__perc: Bezetting als percentage
        - air_flow_office_set__m3_s_1: Gewenste luchtstroomsnelheid
        - air_flow_office__m3_s_1: Werkelijke luchtstroomsnelheid

    Raises:
        DataFileError: Als het bezettingsbestand niet gelezen kan worden.
        ProcessingError: Als bezettingsberekening faalt.
        DataValidationError: Als input data ongeldig is.
    """
    if df is None:
        raise create_data_validation_error(
            column='df',
            expected_type='pd.DataFrame',
            actual_value=None,
            custom_message='Input DataFrame is vereist voor bezettingsberekening.'
        )

    if pad is None or pad == "" or pad == "<null>":
        raise create_data_validation_error(
            column='pad',
            expected_type='str (non-empty)',
            actual_value=pad,
            custom_message='Geen geldig bestandspad ontvangen voor bezettingsdata.'
        )

    if not occupancy_mean__p > 0:
        raise create_configuration_error('occupancy_mean__p', '> 0', occupancy_mean__p)

    # Maak een kopie van de input DataFrame om mutatieproblemen in Grasshopper te voorkomen
    df = df.copy()

    # Lees occupancy CSV veilig via een tijdelijke kopie in de tijdelijke map van het systeem
    temp_pad = None
    try:
        fd, temp_pad = tempfile.mkstemp(prefix='ewf_occupancy_', suffix=os.path.splitext(pad)[1])
        os.close(fd)

        # Kopieer origineel
        shutil.copy2(pad, temp_pad)

        # Lees gekopieerde bestand
        df_occ = pd.read_csv(temp_pad, sep=';', decimal=',')

    except FileNotFoundError:
        raise create_file_not_found_error(pad)
    except PermissionError:
        raise create_permission_error(pad, "lezen")
    except Exception as e:
        raise create_processing_error(
            step="CSV lezen",
            message=f"Onverwachte fout bij het lezen van occupancy data: {str(e)}",
            data_info={'file_path': pad, 'error_type': type(e).__name__}
        )
    finally:
        # Ruim de tijdelijke kopie altijd op, ook als het lezen mislukt
        if temp_pad and os.path.exists(temp_pad):
            try:
                os.remove(temp_pad)
            except OSError:
                pass

    # Controleer vereiste kolom
    if 'occupancyperc' not in df_occ.columns:
        raise create_data_validation_error(
            column='occupancyperc',
            expected_type='numeric column',
            actual_value=None
        )

    # Bereken het juiste aantal uren op basis van data lengte
    data_uren = len(df)
    occupancy_uren = len(df_occ)
    # Gebruik de kleinste lengte om mismatch te voorkomen
    target_uren = min(data_uren, occupancy_uren)
    print("aantal uren in simulatie: ",target_uren)
    if data_uren != occupancy_uren:
        print(f"WAARSCHUWING: weerdata heeft {data_uren} uren, bezettingsdata {occupancy_uren} uren; "
              f"de simulatie wordt ingekort tot {target_uren} uren. Controleer of beide bestanden hetzelfde jaar betreffen.")

    # Pas DataFrame aan als nodig
    if len(df) > target_uren:
        df = df.iloc[:target_uren].copy()
    if len(df_occ) > target_uren:
        df_occ = df_occ.iloc[:target_uren].copy()

    df['occupancy__perc'] = df_occ['occupancyperc']
    #Tijd met tijdzone. Gebruikt voor berekening van zonnestand
    #df['tijd met tijdzone'] = df_occ['date and time']

    # Gewenste luchtstroomsnelheid
    flow_max__m3_s_1 = occupancy_mean__p * air_flow_office_set__dm3_s_1_p_1 / dm3_m_3
    flow_min__m3_s_1 = flow_max__m3_s_1 * flow_modulation_depth__0
    df['air_flow_office_set__m3_s_1'] = 0.01 * df['occupancy__perc'] * flow_max__m3_s_1
    # Gewenste luchtstroomsnelheid wordt altijd bereikt in deze simulatie, maar nooit minder dan het minimum dat de ventilator ondersteunt 
    df['air_flow_office__m3_s_1'] = np.maximum(df['air_flow_office_set__m3_s_1'], flow_min__m3_s_1)

    #Determine fan efficiency at the current flow
    fan_max__m3_s_1 = flow_max__m3_s_1
    fan_min__m3_s_1 = fan_max__m3_s_1 * fan_modulation_depth__0
    df['eta_fan__W0'] = (eta_fan_min__W0 + (df['air_flow_office__m3_s_1'] - fan_min__m3_s_1) /
                             (fan_max__m3_s_1 - fan_min__m3_s_1) * (eta_fan_max__W0 - eta_fan_min__W0))

    # Creeer een lijst met tijdstippen met tijdzone (geoptimaliseerd)

    
    # Creëer tijd range met juiste lengte
    start = datetime(jaar, 1, 1, 0)
    stop = start + timedelta(hours=target_uren - 1)
    
    # Creëer tijd range met exact juiste lengte
    tijd_range = pd.date_range(start, stop, freq='h', tz='Europe/Amsterdam')
    
    # Voeg tijd kolom toe
    df['tijd met tijdzone'] = tijd_range

    return df