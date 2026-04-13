# Toekomstige ontwikkelmogelijkheden — NED Energy integratie

> **Gebaseerd op:** huidige implementatie (`sensor.py`, `api.py`, `const.py`) en de NED API (`/v1/utilizations`)
> **Doel:** overzicht van uitbreidingen die technisch haalbaar zijn met de bestaande API

---

## Inhoudsopgave

- [Wat er nu is](#wat-er-nu-is)
- [1. CO₂-intensiteit sensoren](#1-co₂-intensiteit-sensoren)
- [2. Voorspelling (forecast) sensoren](#2-voorspelling-forecast-sensoren)
- [3. Extra energietype sensoren](#3-extra-energietype-sensoren)
- [4. Regionale en offshore sensoren](#4-regionale-en-offshore-sensoren)
- [5. Gasnetwerk sensoren](#5-gasnetwerk-sensoren)
- [6. Capaciteit sensoren (kW naast kWh)](#6-capaciteit-sensoren-kw-naast-kwh)
- [7. Afgeleide berekeningen](#7-afgeleide-berekeningen)
- [8. Binary sensors voor automations](#8-binary-sensors-voor-automations)
- [9. HA Energy Dashboard integratie](#9-ha-energy-dashboard-integratie)
- [10. Historische data en long-term statistics](#10-historische-data-en-long-term-statistics)
- [11. Configuratie uitbreidingen](#11-configuratie-uitbreidingen)
- [Prioriteitenmatrix](#prioriteitenmatrix)

---

## Wat er nu is

De integratie levert momenteel **8 sensoren**, allemaal landelijk (point=0), uurresolutie, actuele data:

| Sensor | type | activity |
|---|---|---|
| Total Production | 0 (All) | 1 (Providing) |
| Solar Production | 2 (Solar) | 1 (Providing) |
| Wind Production | 1 (Wind) | 1 (Providing) |
| Fossil Gas Production | 18 (FossilGasPower) | 1 (Providing) |
| Electricity Consumption | 59 (Electricityload) | 2 (Consuming) |
| Energy Import | 27 (ElectricityMix) | 3 (Import) |
| Energy Export | 27 (ElectricityMix) | 4 (Export) |
| Renewable Percentage | *(berekend)* | — |

---

## 1. CO₂-intensiteit sensoren

**Wat:** De API retourneert de velden `emission` (kg CO₂) en `emissionfactor` (kg CO₂/kWh) per record — deze worden nu genegeerd.

**Sensoren:**

| Sensor | Eenheid | Bron |
|---|---|---|
| Grid CO₂ intensity | g CO₂/kWh | `emissionfactor` van ElectricityMix |
| Grid CO₂ emissions | kg CO₂/uur | `emission` van totale consumptie |

**Waarde voor HA:**
- Automatisering: start zware apparaten (vaatwasser, EV-lader, wasmachine) alleen als de CO₂-intensiteit van het net onder een drempelwaarde is.
- Dashboard: inzicht in wanneer stroom vervuilend of schoon is.
- Koppeling met HA's ingebouwde CO₂-signaalkaart (`carbon_intensity` device class bestaat in HA).

**Implementatie:** Minimaal — `emission` en `emissionfactor` zitten al in de API-response maar worden in `_latest_volume()` weggegooid. Nieuwe helperfunctie naast `_latest_volume` en twee extra `SensorEntityDescription`-entries.

---

## 2. Voorspelling (forecast) sensoren

**Wat:** De API heeft een `classification=1` (Forecast) naast de huidige `classification=2` (Current/actueel). Voorspellingsdata is beschikbaar voor solar en wind.

**Sensoren:**

| Sensor | type | classification |
|---|---|---|
| Solar Production Forecast | 2 (Solar) | 1 (Forecast) |
| Wind Production Forecast | 1 (Wind) | 1 (Forecast) |
| Total Production Forecast | 0 (All) | 1 (Forecast) |
| Renewable % Forecast | *(berekend)* | — |

**Waarde voor HA:**
- Slimme EV-lading: laad overdag als de zonneforecast hoog is.
- Energieopslag (thuisbatterij): beslissen wanneer op te laden of te ontladen.
- Proactieve automations die vooruit plannen in plaats van reageren.

**Implementatie:** De `_fetch_utilization()` methode krijgt een extra `classification`-parameter. Nieuwe coordinator-sleutels en sensorbeschrijvingen toevoegen.

---

## 3. Extra energietype sensoren

**Wat:** De API bevat meer energietypen dan de huidige vier. Interessante toevoegingen:

| Type | Waarde | Categorie | Opmerking |
|---|---|---|---|
| Nuclear | 20 | Overig | Borssele kerncentrale |
| Wind Offshore | 17 | Hernieuwbaar | Offshore apart van onshore |
| Wind Offshore B/C | 22, 51 | Hernieuwbaar | Extra offshore clusters |
| Biomass | 13, 25 | Hernieuwbaar | Biomassacentrales |
| Storage In | — | Opslag | activity=5 |
| Storage Out | — | Opslag | activity=6 |
| Waste Power | 21 | Overig | Afvalverbranding |

> **Noot:** De huidige `TYPE_WIND = 1` omvat mogelijk alleen onshore wind. Type 17 (WindOffshore) is apart. Dit is een correctheid-issue in de huidige implementatie dat onderzocht moet worden.

**Waarde voor HA:**
- Completer beeld van de energiemix
- Kernenergie apart zichtbaar (relevant voor politieke discussies / bewustwording)
- Opslag-sensoren: zien wanneer het net batterijen laadt/ontlaadt

**Implementatie:** Nieuwe constanten in `const.py`, extra regels in de `queries`-lijst in `api.py`, nieuwe `SensorEntityDescription`-entries.

---

## 4. Regionale en offshore sensoren

**Wat:** De API biedt data per provincie (points 1–12) en per offshore windpark (points 28–36).

**Provincies (point 1–12):**

| Point | Provincie |
|---|---|
| 1 | Groningen |
| 2 | Friesland |
| 3 | Drenthe |
| 8 | Noord-Holland |
| 9 | Zuid-Holland |
| … | … |

**Offshore windparken (point 14, 28–36):**

| Point | Park |
|---|---|
| 14 | Offshore totaal |
| 31 | Windpark Gemini |
| 33 | Borssele I&II |
| 35 | Hollandse Kust Zuid |
| 36 | Hollandse Kust Noord |

**Waarde voor HA:**
- Gebruikers in een specifieke provincie zien regionale productie.
- Offshore parken zijn interessant voor energiebedrijven of enthousiastelingen die specifieke parken willen volgen.

**Implementatie:**
- Config flow uitbreiden met een `point`-selectie.
- Of: meerdere config entries toestaan (één per regio).
- Aandachtspunt: elke extra regio = extra API-verzoeken, let op rate limiting.

---

## 5. Gasnetwerk sensoren

**Wat:** De API bevat ook gasdata naast elektriciteitsdata.

| Type | Waarde | Omschrijving |
|---|---|---|
| NaturalGas | 23 | Aardgasproductie/-verbruik |
| GasMix | 28 | Gasmix import/export |
| GasDistribution | 31 | Gasdistributie |
| Biomethane | 24 | Groen gas |
| IndustrialConsumersGasCombination | 53 | Industrieel gasverbruik |

**Waarde voor HA:**
- Nederland is een grote gasgebruiker; landelijk gasverbruik als sensor.
- Koppeling met lokale gasverbruiksensoren voor vergelijking.
- Biomethaan-aandeel als alternatieve "groen gas percentage".

**Implementatie:** Aparte groep sensoren met eigen `const.py`-blok. Dezelfde `_fetch_utilization()` kan worden hergebruikt.

---

## 6. Capaciteit sensoren (kW naast kWh)

**Wat:** De API retourneert naast `volume` (kWh) ook `capacity` (kW). Momenteel wordt alleen `volume` gebruikt.

**Sensoren:**

| Sensor | Eenheid | Veld |
|---|---|---|
| Solar Capacity | kW | `capacity` |
| Wind Capacity | kW | `capacity` |
| Total Capacity | kW | `capacity` |

**Waarde voor HA:**
- Capaciteit is het **vermogen op dit moment**, volume is de geproduceerde energie in het afgelopen uur.
- Voor visualisatie in dashboards is capaciteit (kW) intuïtiever dan volume (kWh per uur).
- Koppeling met de HA Energy Dashboard `power` sensor class.

**Implementatie:** `_latest_volume()` hernoemen naar een generiekere helper die ook `capacity` kan teruggeven. Of een tweede helperfunctie `_latest_capacity()`.

---

## 7. Afgeleide berekeningen

**Wat:** Sensoren die niet direct uit de API komen maar worden berekend op basis van meerdere API-waarden.

| Sensor | Formule | Eenheid |
|---|---|---|
| Grid balance | `production + import − export − consumption` | kWh |
| Fossil percentage | `fossil / total * 100` | % |
| Nuclear percentage | `nuclear / total * 100` | % |
| Net self-sufficiency | `(production − export) / consumption * 100` | % |
| Offshore wind share | `offshore_wind / total_wind * 100` | % |

**Waarde voor HA:**
- Grid balance: positief = overschot op het net, negatief = tekort.
- Fossiel percentage: complement van hernieuwbaar percentage.
- Zelfvoorzieningsgraad: hoeveel van het verbruik wordt nationaal gedekt.

**Implementatie:** Uitbreiding van `_calc_renewable_pct()` in `api.py` met extra berekeningen. Geen extra API-calls nodig.

---

## 8. Binary sensors voor automations

**Wat:** `binary_sensor`-entiteiten die aan/uit zijn op basis van drempelwaarden. Ideaal als trigger voor automations.

| Sensor | Aan als | Gebruik |
|---|---|---|
| Grid is Renewable | hernieuwbaar % > instelbare drempel | Start zware apparaten |
| Grid is Low Carbon | CO₂-intensiteit < drempel | EV-lading optimaliseren |
| Solar is Producing | solar production > 0 | Zonneschijndetectie |
| Grid Surplus | import < 0 of balance > 0 | Energieoverschot op het net |

**Waarde voor HA:**
- Directe inzet als trigger in automatiseringen zonder template-sensoren te hoeven schrijven.
- Drempelwaarden instelbaar via config flow of options flow.

**Implementatie:** Nieuw platform-bestand `binary_sensor.py`. Inherits van `CoordinatorEntity` net als de huidige sensoren. Drempelwaarden opslaan als `ConfigEntry.options`.

---

## 9. HA Energy Dashboard integratie

**Wat:** De ingebouwde HA Energy Dashboard (Instellingen → Energie) verwacht sensoren met `device_class=ENERGY` en `state_class=TOTAL_INCREASING` of via de `statistics` platform.

**Huidige situatie:** De sensoren gebruiken `state_class=MEASUREMENT` — ze zijn **niet** zichtbaar in het Energy Dashboard.

**Uitbreiding:**
- Toevoegen van `long_term_statistics` via `StatisticsShim` of een aparte `statistics` sensor.
- Alternatief: de integratie registreren als externe energiebron via `homeassistant.components.energy`.

**Waarde voor HA:**
- Landelijke productie/consumptie vergelijken met eigen thuisdata in één dashboard.
- Automatisch historische grafieken zonder extra Lovelace-configuratie.

**Implementatie:** Relatief complex — vereist begrip van HA's statistics-API. Goede referentie: `homeassistant/components/energy` in de HA core.

---

## 10. Historische data en long-term statistics

**Wat:** De NED API kan historische data teruggeven door de datumfilters aan te passen. Dat maakt het mogelijk om bij het instellen van de integratie de HA statistics-database te vullen met historische waarden.

**Mogelijkheden:**
- **Backfill bij eerste installatie:** de afgelopen 30 of 90 dagen importeren in de HA-statistieken.
- **Dagelijkse/maandelijkse aggregaties:** met `granularity=6/7` en `granularitytimezone=1` (CET) dagelijkse en maandelijkse totalen ophalen.

**Waarde voor HA:**
- Historische grafieken direct bij installatie beschikbaar.
- Maandelijkse energierapporten met landelijke vergelijkingsdata.

**Implementatie:** Aparte service (`ned_energy.import_history`) of een eenmalige actie in `async_setup_entry`. Let op: backfill kan veel API-verzoeken kosten — slimme batching en rate-limit bewaking noodzakelijk.

---

## 11. Configuratie uitbreidingen

**Wat:** De huidige config flow vraagt alleen om API-sleutel en scan-interval. Er zijn meer zinvolle instellingen mogelijk.

### Options flow uitbreidingen

| Optie | Type | Standaard | Omschrijving |
|---|---|---|---|
| Regio (point) | Dropdown | 0 (NL totaal) | Provincie of offshore totaal |
| Sensoren inschakelen | Multi-select | Alles aan | Kies welke sensoren actief zijn |
| CO₂ sensor | Toggle | Uit | CO₂-intensiteit inschakelen |
| Forecast sensoren | Toggle | Uit | Voorspellingsdata inschakelen |
| Hernieuwbaar % drempel | Getal (0–100) | 50 | Voor binary sensor |
| CO₂ drempel | Getal g/kWh | 200 | Voor binary sensor |

### Multi-instance ondersteuning

Meerdere config entries toestaan zodat gebruikers bijv. zowel nationale data als een specifieke provincie kunnen volgen. De integratie staat dit al technisch toe (`single_config_entry = False` is de standaard in HA).

---

## Prioriteitenmatrix

| Uitbreiding | Impact | Complexiteit | Prioriteit |
|---|---|---|---|
| CO₂-intensiteit sensor | Hoog | Laag | **Hoog** |
| Capaciteit (kW) sensoren | Middel | Laag | **Hoog** |
| Forecast sensoren | Hoog | Laag | **Hoog** |
| Afgeleide berekeningen (balance, fossil %) | Middel | Laag | **Hoog** |
| Binary sensors voor automations | Hoog | Middel | Middel |
| Extra energietypen (nuclear, offshore, opslag) | Middel | Laag | Middel |
| Gas sensoren | Middel | Laag | Middel |
| Configuratie uitbreidingen (opties) | Middel | Middel | Middel |
| Regionale / provinciale sensoren | Laag | Middel | Laag |
| HA Energy Dashboard integratie | Hoog | Hoog | Laag |
| Historische data backfill | Middel | Hoog | Laag |

> **Aanbeveling om mee te starten:** CO₂-intensiteit, capaciteit-sensoren en forecast zijn alle drie kleine aanpassingen in bestaande code met hoge gebruikswaarde. Daarna binary sensors voor automation-gebruik.
