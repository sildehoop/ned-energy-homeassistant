# NED API — Technische documentatie

> **Bron:** [ned.nl](https://ned.nl) — Nationaal Energiedashboard
> **Swagger UI:** [api.ned.nl/v1](https://api.ned.nl/v1)
> **Type:** RESTful OpenAPI

---

## Inhoudsopgave

- [Toegang](#toegang)
- [Rate limiting](#rate-limiting)
- [Request opbouw](#request-opbouw)
- [Response velden](#response-velden)
- [Parameters](#parameters)
  - [Activity](#activity)
  - [Classification](#classification)
  - [Granularity](#granularity)
  - [GranularityTimeZone](#granularitytimezone)
  - [Point](#point)
  - [Type](#type)
  - [Validfrom](#validfrom)
  - [Paginering en sortering](#paginering-en-sortering)
- [Bestandsformaten](#bestandsformaten)
- [Tijdzone gedrag](#tijdzone-gedrag)
- [Historische gegevens](#historische-gegevens)
- [Gebruikte waarden in deze integratie](#gebruikte-waarden-in-deze-integratie)
- [Voorbeeldverzoek](#voorbeeldverzoek)

---

## Toegang

Authenticatie gaat via een API-sleutel die je aanmaakt in je account op [ned.nl](https://ned.nl). De sleutel wordt bij elk verzoek meegestuurd als request-header:

```
X-AUTH-TOKEN: <jouw-api-sleutel>
```

> De sleutel is gekoppeld aan je naam en account. Deel hem niet met anderen.

---

## Rate limiting

| Limiet | Waarde |
|---|---|
| Max. verzoeken | **200 per 5 minuten** |
| Aanbevolen interval | ≥ 60 seconden |

Deze integratie gebruikt standaard een interval van **300 seconden** (5 minuten), wat neerkomt op maximaal 60 verzoeken per 5 minuten — ruim onder de limiet.

---

## Request opbouw

**Endpoint:**
```
GET https://api.ned.nl/v1/utilizations
```

**Verplichte headers:**
```
X-AUTH-TOKEN: <jouw-api-sleutel>
Accept: application/ld+json
```

**Parameters worden als query-string meegegeven:**
```
?point=0&type=2&granularity=5&granularitytimezone=0&classification=2&activity=1
  &validfrom[strictly_before]=2020-11-17&validfrom[after]=2020-11-16
```

---

## Response velden

Een enkel record uit de API-response ziet er als volgt uit:

```json
{
  "@id": "/v1/utilizations/3844522221",
  "@type": "Utilization",
  "type": "/v1/types/2",
  "granularity": "/v1/granularities/3",
  "granularitytimezone": "/v1/granularity_time_zones/0",
  "id": 3844522221,
  "point": "/v1/points/0",
  "activity": "/v1/activities/1",
  "classification": "/v1/classifications/2",
  "capacity": 438626,
  "volume": 73104,
  "emission": null,
  "emissionfactor": null,
  "percentage": 0.05968400090932846,
  "validfrom": "2020-11-16T14:30:00+00:00",
  "validto": "2020-11-16T14:40:00+00:00",
  "lastupdate": "2020-11-19T14:06:04+00:00"
}
```

| Veld | Eenheid | Omschrijving |
|---|---|---|
| `capacity` | kW | Gemiddelde capaciteit over het tijdsinterval |
| `volume` | kWh | Geproduceerd of verbruikt energievolume |
| `percentage` | — | Benuttingsgraad als fractie van de totale capaciteit |
| `emission` | kg CO₂ | CO₂-uitstoot over het interval |
| `emissionfactor` | kg/kWh | Emissiefactor van de energiedrager |
| `validfrom` | ISO 8601 UTC | Begin van het tijdsinterval |
| `validto` | ISO 8601 UTC | Einde van het tijdsinterval |
| `lastupdate` | ISO 8601 UTC | Tijdstip van de laatste bijwerking van dit record |

> **Tip:** Voor visualisatie van opwek gebruik je het gemakkelijkst `capacity`. Voor energieberekeningen gebruik je `volume`.

---

## Parameters

### Activity

Geeft het activiteitstype aan.

| Waarde | Naam | Omschrijving |
|---|---|---|
| `1` | Providing | Opwek / productie |
| `2` | Consuming | Consumptie / verbruik |
| `3` | Import | Invoer over landsgrens |
| `4` | Export | Uitvoer over landsgrens |
| `5` | Storage in | Opslag laden |
| `6` | Storage out | Opslag ontladen |
| `7` | Storage | Totale opslag |

---

### Classification

Geeft het type data aan.

| Waarde | Naam | Omschrijving |
|---|---|---|
| `1` | Forecast | Voorspelling |
| `2` | Current | Actueel / near-realtime |

---

### Granularity

De tijdsresolutie van de data.

| Waarde | Interval | Opmerking |
|---|---|---|
| `3` | 10 minuten | Fijnste resolutie |
| `4` | 15 minuten | |
| `5` | Uur | Gebruikt door deze integratie |
| `6` | Dag | Alleen bij `granularitytimezone=1` (CET) |
| `7` | Maand | Alleen bij `granularitytimezone=1` (CET) |
| `8` | Jaar | Alleen bij `granularitytimezone=1` (CET) |

> **Let op:** Dag-, maand- en jaaraggregaties worden alleen berekend in CET. Gebruik bij deze granulariteiten altijd `granularitytimezone=1`. Bij `granularitytimezone=0` (UTC) worden geen waarden teruggegeven.

---

### GranularityTimeZone

De tijdzone waarbinnen de `validfrom` en `validto` datums worden geïnterpreteerd.

| Waarde | Tijdzone | Opmerking |
|---|---|---|
| `0` | UTC | Gebruik voor 10-min, 15-min en uurdata |
| `1` | CET (Europa/Amsterdam) | Verplicht voor dag/maand/jaar aggregaties |

> De tijdstippen in de response (`validfrom`, `validto`, `lastupdate`) zijn **altijd in UTC**, ongeacht de gekozen `granularitytimezone`.

---

### Point

Het geografische gebied van de data.

| Waarde | Gebied |
|---|---|
| `0` | Nederland (totaal) |
| `1` | Groningen |
| `2` | Friesland |
| `3` | Drenthe |
| `4` | Overijssel |
| `5` | Flevoland |
| `6` | Gelderland |
| `7` | Utrecht |
| `8` | Noord-Holland |
| `9` | Zuid-Holland |
| `10` | Zeeland |
| `11` | Noord-Brabant |
| `12` | Limburg |
| `14` | Offshore (totaal) |
| `28` | Windpark Luchterduinen |
| `29` | Windpark Princes Amalia |
| `30` | Windpark Egmond aan Zee |
| `31` | Windpark Gemini |
| `33` | Windpark Borssele I&II |
| `34` | Windpark Borssele III&IV |
| `35` | Windpark Hollandse Kust Zuid |
| `36` | Windpark Hollandse Kust Noord |

---

### Type

Het type energiedrager of -mix.

| Waarde | Naam | Categorie |
|---|---|---|
| `0` | All | Alle typen |
| `1` | Wind | Hernieuwbaar |
| `2` | Solar | Hernieuwbaar |
| `3` | Biogas | Hernieuwbaar |
| `4` | HeatPump | Hernieuwbaar |
| `8` | Cofiring | Overig |
| `9` | Geothermal | Hernieuwbaar |
| `10` | Other | Overig |
| `11` | Waste | Overig |
| `12` | BioOil | Hernieuwbaar |
| `13` | Biomass | Hernieuwbaar |
| `14` | Wood | Hernieuwbaar |
| `17` | WindOffshore | Hernieuwbaar |
| `18` | FossilGasPower | Fossiel |
| `19` | FossilHardCoal | Fossiel |
| `20` | Nuclear | Overig |
| `21` | WastePower | Overig |
| `22` | WindOffshoreB | Hernieuwbaar |
| `23` | NaturalGas | Fossiel |
| `24` | Biomethane | Hernieuwbaar |
| `25` | BiomassPower | Hernieuwbaar |
| `26` | OtherPower | Overig |
| `27` | ElectricityMix | Mix (import/export) |
| `28` | GasMix | Mix |
| `31` | GasDistribution | Gas |
| `35` | WKK Total | Warmtekrachtkoppeling |
| `50` | SolarThermal | Hernieuwbaar |
| `51` | WindOffshoreC | Hernieuwbaar |
| `53` | IndustrialConsumersGasCombination | Consumptie |
| `54` | IndustrialConsumersPowerGasCombination | Consumptie |
| `55` | LocalDistributionCompaniesCombination | Consumptie |
| `56` | AllConsumingGas | Consumptie |
| `59` | Electricityload | Consumptie |

---

### Paginering en sortering

De `/utilizations` endpoint retourneert een gepagineerde collectie.

| Parameter | Standaard | Max | Omschrijving |
|---|---|---|---|
| `page` | `1` | — | Paginanummer |
| `itemsPerPage` | `144` | `200` | Aantal records per pagina |
| `order[validfrom]` | `desc` | — | Sorteervolgorde: `asc` of `desc` |

> **Tip:** De standaard van 144 items komt overeen met een volledige dag aan 10-minuutdata. Bij uurdata (`granularity=5`) zijn 24 items genoeg voor één dag.

Alle filterparameters (`point`, `type`, `activity`, `classification`, `granularity`, `granularitytimezone`) accepteren ook een **array-syntax** voor meerdere waarden tegelijk:

```
?point[]=0&point[]=8&type[]=1&type[]=2
```

---

### Validfrom

Datumfilter voor het tijdsinterval van de data. Gebruik `[mod]` als modifier:

| Modifier | Betekenis |
|---|---|
| `validfrom[after]` | Vanaf (inclusief) deze datum |
| `validfrom[strictly_after]` | Strikt na (exclusief) deze datum |
| `validfrom[before]` | Tot en met (inclusief) deze datum |
| `validfrom[strictly_before]` | Strikt voor (exclusief) deze datum |

**Formaat:** `YYYY-MM-DD`

**Voorbeeld** — data van 16 november 2020:
```
validfrom[after]=2020-11-16&validfrom[strictly_before]=2020-11-17
```

---

## Bestandsformaten

De API ondersteunt de volgende formaten via de `Accept`-header:

| Format | Accept-header waarde |
|---|---|
| JSON-LD | `application/ld+json` |
| JSON-HAL | `application/hal+json` |
| JSON-API | `application/vnd.api+json` |
| JSON | `application/json` |
| XML | `application/xml` |
| CSV | `text/csv` |
| HTML | `text/html` |

---

## Tijdzone gedrag

| Situatie | Gedrag |
|---|---|
| `granularitytimezone=0` (UTC) | `validfrom`/`validto` worden als UTC-datum geïnterpreteerd |
| `granularitytimezone=1` (CET) | `validfrom`/`validto` worden als CET-datum geïnterpreteerd |
| Dag/maand/jaar aggregaties | Alleen beschikbaar met `granularitytimezone=1` |
| Response timestamps | Altijd UTC, ongeacht de gekozen timezone |

---

## Historische gegevens

Historische data kan achteraf worden bijgewerkt. Het veld `lastupdate` geeft aan wanneer een record voor het laatst is herberekend. Dit betekent **niet** dat de intervalwaarde zelf veranderd is.

Redenen voor bijwerking:
- Wijzigingen in brondata
- Aanpassingen in modelparameters
- Aanpassingen in het model zelf

Sommige herberekeningen zijn periodiek (dagelijks), andere zijn handmatig op verzoek van het NED.

---

## Gebruikte waarden in deze integratie

De volgende combinaties worden gebruikt door `api.py` in deze integratie. Alle queries gebruiken `point=0` (Nederland totaal), `granularity=5` (uur), `classification=2` (actueel) en `granularitytimezone=0` (UTC).

| Sensor | `type` | `activity` | Constante in `const.py` |
|---|---|---|---|
| Totale productie | `0` (All) | `1` (Providing) | `TYPE_ALL` / `ACTIVITY_PROVIDING` |
| Zonneproductie | `2` (Solar) | `1` (Providing) | `TYPE_SOLAR` |
| Windproductie | `1` (Wind) | `1` (Providing) | `TYPE_WIND` |
| Fossiel gas | `18` (FossilGasPower) | `1` (Providing) | `TYPE_FOSSIL_GAS` |
| Consumptie | `59` (Electricityload) | `2` (Consuming) | `TYPE_ELECTRICITY_LOAD` / `ACTIVITY_CONSUMING` |
| Import | `27` (ElectricityMix) | `3` (Import) | `TYPE_ELECTRICITY_MIX` / `ACTIVITY_IMPORT` |
| Export | `27` (ElectricityMix) | `4` (Export) | `TYPE_ELECTRICITY_MIX` / `ACTIVITY_EXPORT` |
| Hernieuwbaar % | — | — | Berekend: `(solar + wind) / total * 100` |

---

## Voorbeeldverzoek

Zonproductie van Nederland op 16 november 2020, per 10 minuten, in JSON-LD:

**cURL:**
```bash
curl --location -g --request GET \
  'https://api.ned.nl/v1/utilizations?point=0&type=2&granularity=3&granularitytimezone=0&classification=2&activity=1&validfrom[strictly_before]=2020-11-17&validfrom[after]=2020-11-16' \
  --header 'X-AUTH-TOKEN: YourSecretApiKey' \
  --header 'Accept: application/ld+json'
```

**Python:**
```python
import requests

response = requests.get(
    "https://api.ned.nl/v1/utilizations",
    headers={
        "X-AUTH-TOKEN": "YourSecretApiKey",
        "Accept": "application/ld+json",
    },
    params={
        "point": 0,
        "type": 2,
        "granularity": 3,
        "granularitytimezone": 0,
        "classification": 2,
        "activity": 1,
        "validfrom[strictly_before]": "2020-11-17",
        "validfrom[after]": "2020-11-16",
    },
    allow_redirects=False,
)
print(response.json())
```
