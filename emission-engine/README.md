# Emission engine coverage and trust

## Factor inventory and evidence audit

Audit performed on 25 October 2026. The figures below are the values currently
stored in `data/emission_factors.json`; this inventory is not an endorsement of
their accuracy. `India` is the library-wide default reported by the engine,
not per-factor evidence that a value applies to a particular Indian grid,
fuel, technology, or reporting period. All factor records remain
`unverified_demo_value`.

| Engine category | Factor | Factor unit | Activity unit | Basis | Library geography | Reference year | Factor source URL | Normal AI upload match |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `electricity_grid` | 0.710 | kg CO2/kWh | kWh | CO2 | India default; applicability unverified | Not confirmed; legacy record claimed 2025 and library metadata says 2024-25 | [NITI Aayog power-sector report](https://www.niti.gov.in/sites/default/files/2026-02/Scenarios-Towards-Viksit-Bharat-and-Net-Zero-Sectoral-Insights-Power.pdf) | Yes |
| `Fleet Diesel` | 2.687 | kg CO2e/Litre | Litres | CO2e | India default; applicability unverified | Not recorded | None | No |
| `natural_gas` | 0.183 | kg CO2e/kWh | kWh | CO2e | India default; applicability unverified | Not recorded | None | Yes |
| `freight_transport` | 0.602 | kg CO2e/tonne-km | tonne-km | CO2e | India default; applicability unverified | Not recorded | None | Yes |
| `waste_disposal` | 412.0 | kg CO2e/Tonne | Tonnes | CO2e | India default; applicability unverified | Not recorded | None | Yes |
| `business_travel` | 0.158 | kg CO2e/passenger-km | passenger-km | CO2e | India default; applicability unverified | Not recorded | None | Yes |
| `Packaging Materials` | 0.940 | kg CO2e/kg | kg | CO2e | India default; applicability unverified | Not recorded | None | No |
| `Water & Effluent` | 0.344 | kg CO2e/m³ | m³ | CO2e | India default; applicability unverified | Not recorded | None | No |

The electricity record is the only factor with a factor-level URL and a
legacy year claim. At
this audit, the [NITI Aayog PDF](https://www.niti.gov.in/sites/default/files/2026-02/Scenarios-Towards-Viksit-Bharat-and-Net-Zero-Sectoral-Insights-Power.pdf)
could not be retrieved (HTTP 403), so its contents could not be checked against
0.710 kg CO2/kWh, geography, or the intended accounting method. The previous
factor record's 2025 `source_year` conflicts with the library metadata's
2024-25 `electricity_reference_year`; neither could be supported from accessible
source content. The factor's `source_year` is now unset rather than presented
as a confirmed year. The library's
[CEA baseline-database reference](https://cea.nic.in/cdm-co2-baseline-database/?lang=en)
returned HTTP 404 at audit time and is not attached as factor-level evidence.
The accessible [UK Government conversion-factor collection](https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting)
describes factors for UK operations; it does not substantiate an India factor
and no particular UK factor is recorded here.

The other seven values have no factor-level source or reference year. All
records now carry explicit nullable provenance fields for title, publisher,
dataset version, publication/reporting year, factor-specific geography,
activity boundary, and method, plus a rationale describing the gap. Null means
not documented or not substantiated, not a default inferred from another
source. The library has no factor-specific geography or methodology record
for any entry.
For every factor, verification would require an accessible authoritative
source identifying the numeric value, numerator and denominator units, source
year, geography, technology/activity boundary, and applicable calculation
basis/methodology. Until that evidence is reviewed and documented, retain the
existing values only as unverified demo factors; do not treat a URL, library
default, or structurally complete review record as proof of scientific
validity.

## Source review relevant to the unmatched values

The official [IPCC 2006 Guidelines, Volume 2, Chapter 2: Stationary Combustion](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf)
reports separate CO2, CH4, and N2O combustion factors in kg gas/TJ on a net
calorific basis, and notes assumptions about combustion technology and
operating conditions. Its natural-gas defaults therefore do not, by
themselves, substantiate this library's 0.183 kg CO2e/kWh factor or a
geography-specific fuel composition.
The official [IPCC 2006 Guidelines, Volume 2, Chapter 3: Mobile Combustion](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf)
Table 3.2.1 gives a default 74,100 kg CO2/TJ for road gas/diesel oil and says
to use country-specific net calorific values and fuel factors where possible.
That is a combustion-only, energy-based CO2 factor, not the stored
2.687 kg CO2e/Litre factor, so it cannot verify the stored diesel value without
fuel-specific conversion data and separately supported non-CO2/upstream
emissions.

The [IPCC Volume 5, Chapter 3: Solid Waste Disposal](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/5_Volume5/V5_3_Ch3_SWDS.pdf)
requires waste composition and disposal-site/treatment characteristics in its
first-order decay model; it does not establish a universal 412 kg CO2e/Tonne
for unspecified waste. [Chapter 6: Wastewater Treatment and Discharge](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/5_Volume5/V5_6_Ch6_Wastewater.pdf)
calculates emissions by wastewater pathway using organic loading such as BOD
or COD and treatment methane-correction factors, not a generic cubic-metre
factor for water supply plus effluent.
These national-inventory guidelines were inspected as methodology evidence;
their activity-specific approaches do not substantiate the library's exact
values, and no factors were substituted.

The electricity database pages could not be retrieved at the requested CEA
URL (HTTP 404); the existing NITI PDF URL returned HTTP 403. Thus the latest
CEA database and its user guide, exact metric, and reporting-year workbook
remain uninspected. No accessible, activity-specific evidence was found in
this audit for freight tonne-kilometres, generic passenger-kilometres,
packaging material life-cycle emissions, or the stored waste value. Freight
and passenger factors must identify transport mode, vehicle/fuel, load or
occupancy, and activity boundary; packaging requires material and life-cycle
boundary evidence; waste requires material and treatment-route evidence.
Sources with different geography or unmatched activity boundaries are not
used as substitute evidence.

## Verification controls

Per-factor provenance fields are explicit and nullable; missing source facts
are not inferred from the India library default. A factor cannot be surfaced
as verified by the engine unless its review evidence identifies the source
location and supporting excerpt and matches the exact factor, category, units,
source year, geography, activity boundary, method, and source metadata. This
is a consistency gate, not a way to authenticate a document or independently
prove scientific correctness: a qualified human must inspect the cited
authoritative source and attest to the match. When that review is missing or
incomplete, the result status is returned as unverified.

## Calculation and integration behavior

The engine requires an exact category and compatible activity unit. It does
not infer activity from invoice spend or convert between unlike units. Factor
denominators are checked against each record's activity unit before use.

The three entries that do not match the classifier's category keys (`Fleet
Diesel`, `Packaging Materials`, and `Water & Effluent`) are not reachable
through the normal AI upload flow. They are not evidence of support for
`mobile_fuel_diesel`, `stationary_fuel_diesel`, `purchased_goods`, or
`water_effluent`. Those activities, paper/stationery, petrol, and other
unmatched categories require manual review and are skipped.

The result reports CO2 separately from CO2e. Dashboard, invoice-summary, and
report totals use eligible uploaded CO2e results only; CO2-only, skipped,
failed, and invalid results are excluded. Synthetic demo values are calculated
and shown separately, never added to uploaded totals. Detailed invoice results
and CSV rows retain their basis, unit, provenance, and verification state. A
structurally complete verification record only describes review metadata and
does not establish scientific correctness.
