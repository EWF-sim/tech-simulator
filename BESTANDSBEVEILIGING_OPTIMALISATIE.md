# Bestandsbeveiliging bij het lezen van CSV-bestanden

## Achtergrond

Bij het selecteren van CSV-bestanden in Grasshopper werden bestanden verwijderd of vergrendeld doordat de Python-componenten ze direct lazen. De kernmodules lezen de invoerbestanden daarom via een tijdelijke kopie.

## Huidige werking

Dit geldt voor `src/weather.py` (`safe_read_csv`) en `src/occupancy.py` (`calculate_occupancy`):

1. Het pad wordt gecontroleerd (niet leeg, niet `<null>`; alleen `weather.py`).
2. Naast het origineel wordt een kopie gemaakt met de naam `<bestandsnaam>_temp<extensie>`.
3. De kopie wordt gelezen met `pd.read_csv` (`sep=";"`; voor bezetting ook `decimal=","`).
4. De kopie wordt verwijderd; het origineel blijft ongewijzigd.

Fouten worden vertaald naar de uitzonderingen uit `src/exceptions.py`:

| Situatie | Uitzondering |
| --- | --- |
| Bestand niet gevonden | `DataFileError` (`create_file_not_found_error`) |
| Geen toegang | `DataFileError` (`create_permission_error`) |
| Ontbrekend of ongeldig pad | `DataValidationError` |
| Overige leesfouten | `ProcessingError` |

Uitzonderingen uit `EWFException` worden niet opnieuw verpakt, zodat de specifieke melding bij de aanroeper aankomt.

## Beperkingen

- De tijdelijke kopie staat in dezelfde map als het origineel. Daarvoor is schrijfrechten in die map nodig.
- Als het lezen mislukt, blijft `<bestandsnaam>_temp<extensie>` achter.
- Een bestaand bestand met die naam wordt overschreven en daarna verwijderd.
- Twee gelijktijdige berekeningen op hetzelfde bestand kunnen elkaars kopie overschrijven.

## Wat dit document niet meer beschrijft

Eerdere versies van dit document noemden `export.py`, een `SimulationComponent`-klasse in `ewf_utils.py`, en het lezen en schrijven van parquet-bestanden. Die bestaan niet meer. Het exporteren naar Excel gebeurt nu in het Grasshopper-component *Input export* in `ewf_tech_simulator.ghx`.
