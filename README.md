## Kontrolgruppen – Orientering af beskæftigelse

Automatisering der orienterer borgere med igangværende kontrolsager om deres beskæftigelsesstatus i Momentum.

## Hvad gør robotten?

1. **Henter sagsskabeloner** fra SBSYS og finder ID'er for de relevante kontrolgruppeskabeloner
2. **Søger aktive sager** (status 6) på tværs af de fundne skabeloner
3. **Deduplicerer** – hvis en borger har flere sager, behandles borgeren kun én gang
4. **Fylder arbejdskøen** med unikke CPR-numre
5. **Henter borgerens markeringer** i Momentum og tjekker om der allerede findes en aktiv markering af typen _"Igangværende kontrolgruppe sag"_
6. **Opretter markering** i Momentum hvis den ikke allerede eksisterer
7. **Tracker opgaven** i Odense SQL Server

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø)
- Adgang til **SBSYS** (produktion)
- Adgang til **Momentum** (produktion)
- En **Odense SQL Server**-konto til tracking

## Installation

```sh
uv sync
```

## Konfiguration

Legitimationsoplysninger hentes udelukkende via Automation Server Credentials:

| Credential-navn           | Beskrivelse                        |
|---------------------------|------------------------------------|
| `Odense SQL Server`       | Tracking-database                  |
| `Momentum - produktion`   | Momentum API                       |
| `SBSYS - produktion`      | SBSYS API                          |

## Kørsel

```sh
# Fyld arbejdskøen med borgere fra aktive kontrolsager
uv run python main.py --queue

# Behandl arbejdskøen
uv run python main.py
```

## Afhængigheder

| Pakke                       | Formål                        |
|-----------------------------|-------------------------------|
| `automation-server-client`  | Arbejdskø-håndtering          |
| `sbsys`                     | Integration med SBSYS         |
| `momentum-client`           | Integration med Momentum      |
| `odk-tools`                 | Aktivitetssporing             |

## Persondatasikkerhed

Robotten behandler følsomme personoplysninger på vegne af Odense Kommune, herunder CPR-numre (særlige kategorier jf. GDPR art. 10).

- Ingen personoplysninger må lægges i dette repository — hverken som testdata, i kode eller i kommentarer
- CPR-numre logges aldrig — heller ikke ved fejl
- Legitimationsoplysninger håndteres udelukkende via Automation Server Credentials og må aldrig hardkodes
